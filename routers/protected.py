import uuid

from fastapi import APIRouter, Depends
from utils.auth import get_current_user

router = APIRouter()

@router.get("/dashboard", dependencies=[Depends(get_current_user)])
async def protected_dashboard(user_id: uuid = Depends(get_current_user)):
    """Example protected route requiring authentication."""
    return {"message": "Access granted", "user_id": user_id}
