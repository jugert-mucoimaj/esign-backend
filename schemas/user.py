import uuid
from typing import Optional

from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    phone: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GoogleLoginRequest(BaseModel):
    email: EmailStr
    first_name: Optional[str] = "Unknown"
    last_name: Optional[str] = ""


class UserResponse(BaseModel):
    message: str

    class Config:
        from_attributes = True

class SignDocumentRequest(BaseModel):
    document: str

class UserDB(UserResponse):
    hashed_password: str

class KeyRetrieveRequest(BaseModel):
    password: str

class KeyRetrieveResponse(BaseModel):
    public_key: str
    private_key: str
