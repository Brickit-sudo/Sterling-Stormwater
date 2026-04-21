import asyncio
from app.db.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.services.auth import hash_password


async def seed():
    async with AsyncSessionLocal() as db:
        user = User(
            email="brolfe@sterlingstormwater.com",
            name="B. Rolfe",
            hashed_password=hash_password("changeme123"),
            role=UserRole.super_admin,
        )
        db.add(user)
        await db.commit()
        print("Admin created:", user.email)


asyncio.run(seed())
