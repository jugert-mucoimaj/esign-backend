import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
from models.keys import KeyPair
from models.user import User
from schemas.user import UserCreate, UserResponse, KeyRetrieveResponse, KeyRetrieveRequest, UserLogin, \
    GoogleLoginRequest
from utils.auth import hash_password, create_access_token, verify_password, get_current_user
from utils.crypto import generate_rsa_key_pair, encrypt_private_key, decrypt_private_key, generate_encryption_key
from dotenv import load_dotenv
import os

load_dotenv()
router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")


async def get_user_by_email(email: str, db: AsyncSession):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


@router.post("/google-login")
async def google_login(data: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    """Accepts Google login without verifying the token."""

    email = data.email  # Just take email from frontend
    first_name = data.first_name or "Unknown"
    last_name = data.last_name or ""

    # Check if user exists
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if not user:
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone="",
            hashed_password=""  # No password for OAuth users
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        user = new_user

    access_token = create_access_token(data={"sub": str(user.id)})

    return {
        "message": "Login successful",
        "access_token": access_token,
    }


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):

    # Check if user exists
    result = await db.execute(select(User).where((User.email == user_data.email) | (User.phone == user_data.phone)))
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

    # ✅ Generate PBKDF2 Salt (store this)
    encryption_salt = os.urandom(16)

    new_user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        email=user_data.email,
        hashed_password=hash_password(user_data.password),  # For login
        encryption_salt=encryption_salt,  # Store only the salt!
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    public_key, private_key = generate_rsa_key_pair()

    encrypted_private_key = encrypt_private_key(private_key, new_user.hashed_password, encryption_salt)


    key_pair = KeyPair(user_id=new_user.id, public_key=public_key, private_key=encrypted_private_key)
    db.add(key_pair)
    await db.commit()

    return {
        "message": "User registered successfully. Please proceed to login."
    }


@router.post("/retrieve_keys", response_model=KeyRetrieveResponse)
async def retrieve_keys(
        user_id: uuid.UUID = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Retrieves a user's keys without requiring a password input. Uses stored PBKDF2 key."""

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    key_result = await db.execute(select(KeyPair).where(KeyPair.user_id == user_id))
    key_pair = key_result.scalars().first()

    if not key_pair:
        raise HTTPException(status_code=404, detail="Key pair not found")

    try:
        # ✅ Decrypt private key using stored PBKDF2 key
        decrypted_private_key = decrypt_private_key(key_pair.private_key, user.hashed_password, user.encryption_salt)

    except Exception:
        raise HTTPException(status_code=400, detail="Decryption failed due to incorrect key")

    return KeyRetrieveResponse(
        public_key=key_pair.public_key,
        private_key=decrypted_private_key.decode()
    )


@router.post("/login")
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Handles user login and returns JWT access token."""

    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalars().first()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
