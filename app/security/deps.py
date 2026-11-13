"""get_current_user: put it on any route that needs a logged-in user."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.security.jwt_handler import verify_token

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = verify_token(creds.credentials) if creds else None
    user = await db.get(User, payload.get("user_id")) if payload else None
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in or session expired",
                            headers={"WWW-Authenticate": "Bearer"})
    return user
