from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.models.user import User
from app.routers.dashboard import get_current_user
from app.services.vercel_service import (
    VercelError, deploy_html, is_vercel_configured, make_project_name, project_prefix,
)

router = APIRouter(prefix="/deploy", tags=["Deploy"])

MAX_HTML_BYTES = 5 * 1024 * 1024


class DeploySchema(BaseModel):
    html: str = Field(min_length=1)
    name: str | None = None      # label for a new site (usually the prompt)
    project: str | None = None   # project returned by an earlier deploy -> redeploy to the same URL


@router.get("/status")
async def deploy_status():
    return {"vercel_available": is_vercel_configured()}


@router.post("/vercel")
async def deploy_to_vercel(data: DeploySchema, user: User = Depends(get_current_user)):
    if len(data.html.encode("utf-8")) > MAX_HTML_BYTES:
        raise HTTPException(status_code=413, detail="Site is too large to deploy (5 MB limit).")

    if data.project:
        if not data.project.startswith(project_prefix(user.id)):
            raise HTTPException(status_code=403, detail="That deployment belongs to another account.")
        project = data.project
    else:
        project = make_project_name(user.id, data.name)

    try:
        return await deploy_html(data.html, project)
    except VercelError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
