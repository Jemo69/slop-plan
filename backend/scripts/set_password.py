"""Set password for an existing user.

Usage:
    cd backend && python -m scripts.set_password
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tortoise import Tortoise
from tortoise_conf import TORTOISE_ORM, IS_REMOTE
from models import User
from services import hash_password

EMAIL = "jemolife69@gmail.com"
PASSWORD = "jemolife69."


async def main():
    await Tortoise.init(config=TORTOISE_ORM)

    if IS_REMOTE:
        conn = Tortoise.get_connection("default")
        try:
            await conn.execute_query(
                "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) DEFAULT NULL"
            )
            print("Added password_hash column to users table")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("password_hash column already exists")
            else:
                print(f"Migration note: {e}")

    await Tortoise.generate_schemas()

    user = await User.filter(email=EMAIL).first()
    if not user:
        print(f"User {EMAIL} not found")
        await Tortoise.close_connections()
        return

    user.password_hash = hash_password(PASSWORD)
    await user.save()
    print(f"Password set for {EMAIL}")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
