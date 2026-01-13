from fastapi import APIRouter
from api.api_routes import invitation_router, keys_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(keys_router)
api_router.include_router(invitation_router)