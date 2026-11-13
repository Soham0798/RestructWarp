"""Step 30 (F5): score a page with axe-core, fix the problems, score again.

Fixes come from the LLM when one is configured, otherwise from RULE_FIXES; the fixed page is
kept only if its score really went up.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from openai import AsyncOpenAI

from app.services import llm_service

CHECKER = Path(__file__).resolve().parents[2] / "a11y" / "check.mjs"
PENALTY = {"critical": 10, "serious": 6, "moderate": 3, "minor": 1}


class AuditUnavailable(RuntimeError):
    """Node or the a11y packages are missing (run `npm install` in backend/a11y)."""


def audit(html: str) -> dict:
    node = shutil.which("node")
    if not node or not (CHECKER.parent / "node_modules" / "axe-core").exists():
        raise AuditUnavailable("Install Node.js and run `npm install` in backend/a11y")
    out = subprocess.run([node, str(CHECKER)], input=html, capture_output=True, text=True,
                         encoding="utf-8", timeout=60, check=True)
    violations = json.loads(out.stdout or "[]")
    lost = sum(PENALTY.get(v["impact"], 3) * v["nodes"] for v in violations)
    return {"score": max(0, 100 - lost), "violations": violations}


def _attr_fix(html: str, tag: str, needs: str, value_from) -> str:
    def fix(m):
        el = m.group(0)
        if re.search(rf"\s{needs}=", el):
            return el
        return el[:-1].rstrip("/").rstrip() + f' {needs}="{value_from(el)}"' + ("/>" if el.endswith("/>") else ">")
    return re.sub(rf"<{tag}\b[^>]*>", fix, html)


def _labelled(html: str, el: str) -> bool:
    m = re.search(r'\sid="([^"]+)"', el)
    return bool(re.search(r"aria-label(ledby)?=", el) or (m and f'for="{m.group(1)}"' in html))


def _label_from(el: str) -> str:
    for attr in ("placeholder", "name", "id"):
        if m := re.search(rf'\s{attr}="([^"]+)"', el):
            return m.group(1).replace("_", " ")
    return "Field"


def rule_fixes(html: str) -> str:
    if not re.search(r"<html[^>]*\slang=", html):
        html = re.sub(r"<html\b", '<html lang="en"', html, count=1)
    if "<title>" not in html:
        html = html.replace("</head>", "  <title>Page</title>\n</head>", 1)
    html = _attr_fix(html, "img", "alt", lambda el: "Image")
    for tag in ("input", "select", "textarea"):
        html = re.sub(rf"<{tag}\b[^>]*>",
                      lambda m: m.group(0) if _labelled(html, m.group(0)) or 'type="hidden"' in m.group(0)
                      else m.group(0)[:-1].rstrip("/").rstrip() + f' aria-label="{_label_from(m.group(0))}">', html)
    html = re.sub(r"<(button|a)\b([^>]*)>\s*</\1>",
                  lambda m: m.group(0) if "aria-label" in m.group(2)
                  else f'<{m.group(1)}{m.group(2)} aria-label="{m.group(1).title()}"></{m.group(1)}>', html)
    if "<main" not in html:
        html = re.sub(r"(<body[^>]*>)", r"\1\n<main>", html, count=1).replace("</body>", "</main>\n</body>", 1)
    return html


async def improve(html: str, client: Optional[AsyncOpenAI] = None, rounds: int = 2) -> dict:
    """Returns {html, before, after, how, violations} where how is 'llm', 'rules' or 'none'."""
    first = audit(html)
    best, best_score, how = html, first["score"], "none"
    current = first
    for _ in range(rounds):
        if not current["violations"]:
            break
        candidate, source = None, "rules"
        try:
            reply = await llm_service.chat([
                {"role": "system", "content": "Fix these accessibility violations in the HTML. Keep the design, "
                                              "content and classes. Reply with the complete fixed HTML only."},
                {"role": "user", "content": json.dumps(current["violations"]) + "\n\n" + best}], client=client)
            m = re.search(r"<!doctype html.*</html>", reply, re.S | re.I)
            candidate, source = (m.group(0) if m else None), "llm"
        except llm_service.LLMUnavailable:
            pass
        if not candidate:
            candidate, source = rule_fixes(best), "rules"
        current = audit(candidate)
        if current["score"] <= best_score:
            break
        best, best_score, how = candidate, current["score"], source
    return {"html": best, "before": first["score"], "after": best_score, "how": how,
            "violations": audit(best)["violations"] if how != "none" else first["violations"]}
