import asyncio
from sqlalchemy.future import select
from app.database import AsyncSessionLocal
from app.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def force_create_admin():
    async with AsyncSessionLocal() as db:
        email = "dev@bobthebuilder.ai"
        
        # Check if exists and explicitly delete
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if user:
            print("Deleting existing user for clean slate...")
            await db.delete(user)
            await db.commit()
            
        print("Creating brand new developer user...")
        hashed_password = pwd_context.hash("dev123")
        new_user = User(
            email=email, 
            password=hashed_password, 
            role="developer", 
            credits=999999999
        )
        db.add(new_user)
        await db.commit()
        
        # Verify the commit
        verify_rc = await db.execute(select(User).where(User.email == email))
        user_verification = verify_rc.scalar_one_or_none()
        if user_verification:
             print(f"VERIFIED in BD: role={user_verification.role}, credits={user_verification.credits}")
        else:
             print("FAILED to create!")

if __name__ == "__main__":
    asyncio.run(force_create_admin())
