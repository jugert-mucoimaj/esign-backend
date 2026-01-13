import secrets
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import selectinload

from models import User
from models.api_key import ApiKey
from database import get_db

# Security scheme: API Key in headers
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=True)


def generate_api_key() -> str:
    """Generates a new hashed API key."""
    raw_key = f"ESIGN-{secrets.token_urlsafe(32)}"
    hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, hashed_key  # Return both raw and hashed key


async def store_api_key(user_id: str, session: AsyncSession) -> str:
    """Generates and stores an API key for a user."""
    raw_key, hashed_key = generate_api_key()

    # Store in DB
    api_key_entry = ApiKey(user_id=user_id, api_key=hashed_key)
    session.add(api_key_entry)
    await session.commit()

    return raw_key  # Only return raw key to user


async def verify_api_key(api_key: str, session: AsyncSession) -> ApiKey:
    """Verifies an API key and loads the associated user relationship properly."""
    hashed_key = hashlib.sha256(api_key.encode()).hexdigest()

    result = await session.execute(
        select(ApiKey).options(selectinload(ApiKey.user))  # ✅ Ensure User relationship is preloaded
        .where(ApiKey.api_key == hashed_key, ApiKey.is_active == True)
    )

    api_key_obj = result.scalars().first()

    if not api_key_obj:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return api_key_obj


async def get_api_key_user(api_key: str = Security(api_key_header), session: AsyncSession = Depends(get_db)):
    """Dependency to get user from API key, ensuring relationships are preloaded."""

    result = await session.execute(
        select(ApiKey)
        .options(selectinload(ApiKey.user).selectinload(User.api_keys))  # ✅ Correctly load user + api_keys
        .where(ApiKey.api_key == hashlib.sha256(api_key.encode()).hexdigest(), ApiKey.is_active == True)
    )

    api_key_obj = result.scalars().first()

    if not api_key_obj:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return api_key_obj.user