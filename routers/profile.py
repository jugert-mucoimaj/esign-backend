import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db
from models.user import User
from models.keys import KeyPair
from utils.auth import get_current_user, hash_password, verify_password

router = APIRouter()


class ProfileResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    phone: str
    email: str
    has_key_pair: bool

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None


class ProfileDeleteRequest(BaseModel):
    password: str


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the current user's profile."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    key_result = await db.execute(select(KeyPair).where(KeyPair.user_id == user_id))
    has_key_pair = key_result.scalars().first() is not None

    return ProfileResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        email=user.email,
        has_key_pair=has_key_pair
    )


@router.put("/profile", response_model=ProfileResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update the current user's profile."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if profile_data.first_name is not None:
        user.first_name = profile_data.first_name
    if profile_data.last_name is not None:
        user.last_name = profile_data.last_name
    if profile_data.phone is not None:
        phone_check = await db.execute(
            select(User).where(User.phone == profile_data.phone, User.id != user_id)
        )
        if phone_check.scalars().first():
            raise HTTPException(status_code=400, detail="Phone number already in use")
        user.phone = profile_data.phone
    if profile_data.password is not None:
        user.hashed_password = hash_password(profile_data.password)

    await db.commit()
    await db.refresh(user)

    key_result = await db.execute(select(KeyPair).where(KeyPair.user_id == user_id))
    has_key_pair = key_result.scalars().first() is not None

    return ProfileResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        email=user.email,
        has_key_pair=has_key_pair
    )


@router.delete("/profile")
async def delete_account(
    delete_request: ProfileDeleteRequest,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete the current user's account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(delete_request.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Password is incorrect")

    await db.delete(user)
    await db.commit()

    return {"message": "Account deleted successfully"}