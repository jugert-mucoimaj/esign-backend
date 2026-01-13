from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.api_key import ApiKey
from database import get_db
from utils.api_auth import store_api_key, get_api_key_user

router = APIRouter(prefix="/keys", tags=["API - Keys"])


@router.post("/generate", response_model=dict)
async def generate_new_api_key(user=Depends(get_api_key_user), session: AsyncSession = Depends(get_db)):
    """Generates a new API key, replacing the old one."""
    await session.execute(select(ApiKey).where(ApiKey.user_id == user.id).delete())
    await session.commit()

    new_key = await store_api_key(user.id, session)
    return {"api_key": new_key}


@router.get("/check", response_model=dict)
async def check_api_key_status(user=Depends(get_api_key_user)):
    """Check the current user's API key and its tier."""
    return {"api_key": "Active", "tier": user.api_keys[0].tier}


@router.post("/revoke", response_model=dict)
async def revoke_api_key(user=Depends(get_api_key_user), session: AsyncSession = Depends(get_db)):
    """Revokes the current API key."""
    api_key_entry = await session.execute(select(ApiKey).where(ApiKey.user_id == user.id))
    api_key_obj = api_key_entry.scalars().first()

    if not api_key_obj:
        raise HTTPException(status_code=404, detail="No API key found")

    api_key_obj.is_active = False
    await session.commit()

    return {"message": "API key revoked successfully"}