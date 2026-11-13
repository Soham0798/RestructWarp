from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base, AsyncSessionLocal
from app.services.auth_service import ensure_dev_account
from app.routers import auth, generate, dashboard, admin, deploy
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
