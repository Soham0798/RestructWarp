"""Deploys generated sites to Vercel through its REST API.

Generated output is a single self-contained HTML document, so a deployment is
one inline `index.html` with no build step.
"""
import asyncio
import re
import secrets

import httpx

from app.config import settings

VERCEL_API = "https://api.vercel.com"
POLL_INTERVAL_S = 1.5
POLL_TIMEOUT_S = 90


class VercelError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def is_vercel_configured() -> bool:
    return bool(settings.VERCEL_TOKEN)


def project_prefix(user_id: int) -> str:
    """Every project a user deploys is namespaced so users can't overwrite each other's sites."""
    return f"rw-u{user_id}-"


# Vercel shortens long project names when it builds the <project>.vercel.app domain,
# which drops whatever comes last. Keep names short and put the unique id first so
# every deploy gets its own clearly different URL.
MAX_PROJECT_NAME = 32


def make_project_name(user_id: int, label: str | None) -> str:
    base = f"{project_prefix(user_id)}{secrets.token_hex(3)}"
    room = MAX_PROJECT_NAME - len(base) - 1
    slug = re.sub(r"[^a-z0-9]+", "-", (label or "").lower()).strip("-")[:max(room, 0)].strip("-")
    return f"{base}-{slug}" if slug else base


def _params() -> dict:
    params = {"skipAutoDetectionConfirmation": "1"}
    if settings.VERCEL_TEAM_ID:
        params["teamId"] = settings.VERCEL_TEAM_ID
    return params


def _error_message(res: httpx.Response) -> str:
    try:
        return res.json()["error"]["message"]
    except Exception:
        return f"Vercel returned HTTP {res.status_code}"


async def deploy_html(html: str, project_name: str) -> dict:
    """Creates a production deployment and waits until it is live.

    Returns {"url", "project", "deployment_id"}.
    """
    if not is_vercel_configured():
        raise VercelError("Vercel deploys are not configured (VERCEL_TOKEN is missing).", 503)

    body = {
        "name": project_name,
        "target": "production",
        "files": [{"file": "index.html", "data": html}],
        "projectSettings": {
            "framework": None,
            "buildCommand": None,
            "installCommand": None,
            "outputDirectory": None,
        },
    }
    headers = {"Authorization": f"Bearer {settings.VERCEL_TOKEN}"}

    async with httpx.AsyncClient(base_url=VERCEL_API, headers=headers, timeout=30) as client:
        res = await client.post("/v13/deployments", params=_params(), json=body)
        if res.status_code in (401, 403):
            raise VercelError(f"Vercel rejected the server's token: {_error_message(res)}", 502)
        if res.status_code >= 400:
            raise VercelError(_error_message(res), 502)

        deployment = res.json()
        deployment_id = deployment["id"]

        # A deployment turns READY a moment before its production domain is attached,
        # so keep polling until the domain is assigned too.
        waited = 0.0
        while not _is_settled(deployment):
            if waited >= POLL_TIMEOUT_S:
                if deployment.get("readyState") == "READY":
                    break  # live, domain just not reported yet; resolved below
                raise VercelError("Timed out waiting for the Vercel deployment to go live.", 504)
            await asyncio.sleep(POLL_INTERVAL_S)
            waited += POLL_INTERVAL_S
            res = await client.get(f"/v13/deployments/{deployment_id}", params=_params())
            if res.status_code >= 400:
                raise VercelError(_error_message(res), 502)
            deployment = res.json()

        if deployment["readyState"] != "READY":
            raise VercelError(
                deployment.get("errorMessage") or f"Deployment ended in state {deployment['readyState']}.", 502
            )

        # Link to the production domain (<project>.vercel.app). Never fall back to the
        # per-deployment URL silently: on new projects it sits behind Vercel's login wall.
        hosts = [a for a in (deployment.get("alias") or []) if a != deployment.get("url")]
        if not hosts:
            res = await client.get(f"/v9/projects/{project_name}/domains", params=_params())
            if res.status_code < 400:
                hosts = [d["name"] for d in res.json().get("domains", []) if not d.get("redirect")]

    if not hosts:
        raise VercelError(
            "The site was deployed, but Vercel did not report a public domain for it. "
            f"Open project '{project_name}' in the Vercel dashboard to find its URL.", 502
        )
    return {"url": f"https://{min(hosts, key=len)}", "project": project_name, "deployment_id": deployment_id}


def _is_settled(deployment: dict) -> bool:
    state = deployment.get("readyState")
    if state in ("ERROR", "CANCELED"):
        return True
    return state == "READY" and bool(deployment.get("aliasAssigned") or deployment.get("alias"))
