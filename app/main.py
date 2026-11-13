from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base, AsyncSessionLocal
from app.services.auth_service import ensure_dev_account
from app import models  # noqa: F401  (registers every table before create_all)
from app.routers import auth, generate, dashboard, admin, deploy, projects, sketch, sketch_import
from app.middleware.logger import log_requests

app = FastAPI(title="Restruct Warp")

app.middleware("http")(log_requests)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(generate.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(deploy.router)
# Sketch Studio (merged from Sketch2UI): photo of a hand-drawn UI -> pages and exports
app.include_router(projects.router)
app.include_router(sketch.router)
app.include_router(sketch_import.router)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    if settings.DEV_ACCOUNT_EMAIL and settings.DEV_ACCOUNT_PASSWORD:
        async with AsyncSessionLocal() as db:
            await ensure_dev_account(db, settings.DEV_ACCOUNT_EMAIL, settings.DEV_ACCOUNT_PASSWORD)
        print("[startup] Developer account is ready")

@app.get("/")
async def root():
    return {"status": "Backend Running"}
