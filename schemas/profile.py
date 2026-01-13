import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime


class ProfileResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    phone: str
    email: EmailStr
    has_key_pair: bool

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class ProfileDeleteRequest(BaseModel):
    password: str