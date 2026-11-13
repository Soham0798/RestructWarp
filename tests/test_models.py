import asyncio

from sqlalchemy import func, select

from app.database import AsyncSessionLocal, Base, engine
from app.models import Project, Sketch, User


async def _scenario():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        user = User(email="a@example.com", password="hash")
        project = Project(name="Login app", owner=user)
        project.sketches.append(Sketch(image_path="uploads/1.png"))
        db.add(user)
        await db.commit()

        sketch = (await db.execute(select(Sketch))).scalar_one()
        defaults = (user.credits, user.role, sketch.status)

        await db.delete(user)
        await db.commit()
        left = (await db.execute(select(func.count()).select_from(Sketch))).scalar_one()
    return defaults, left


def test_defaults_and_cascade_delete():
    defaults, sketches_left = asyncio.run(_scenario())
    assert defaults == (10, "user", "uploaded")
    assert sketches_left == 0  # deleting a user removes their projects and sketches
