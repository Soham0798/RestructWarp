"""/projects: each user's own projects."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Project, User
from app.schemas.sketch_schema import ProjectIn, ProjectOut
from app.security.deps import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])


async def owned_project(project_id: int, user: User, db: AsyncSession) -> Project:
    project = await db.scalar(select(Project).options(selectinload(Project.sketches))
                              .where(Project.id == project_id, Project.user_id == user.id))
    if not project:  # 404 for other people's projects too, so ids can't be probed
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(data: ProjectIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    project = Project(name=data.name, user_id=user.id)
    db.add(project)
    await db.commit()
    return await owned_project(project.id, user, db)


@router.get("", response_model=list[ProjectOut])
async def list_projects(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.scalars(select(Project).options(selectinload(Project.sketches))
                            .where(Project.user_id == user.id).order_by(Project.updated_at.desc()))
    return list(rows)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await owned_project(project_id, user, db)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.delete(await owned_project(project_id, user, db))
    await db.commit()
