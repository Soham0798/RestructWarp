from passlib.context import CryptContext
from sqlalchemy.future import select
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"])

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)

async def get_user_by_email(db, email: str):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def ensure_dev_account(db, email: str, password: str):
    """Creates the developer account, or resets its role and password if it exists."""
    user = await get_user_by_email(db, email)
    if user is None:
        user = User(email=email)
        db.add(user)
    user.role = "developer"
    user.credits = 999999999
    if not user.password or not verify_password(password, user.password):
        user.password = hash_password(password)
    await db.commit()
