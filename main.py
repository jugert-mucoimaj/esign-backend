from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from routers import auth, protected, sign, profile, invitation
from api import api_router

app = FastAPI(title="eSign API", version="1.0.0", description="A FastAPI-based eSign system")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT authenticated routes (frontend)
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(protected.router, prefix="/protected", tags=["Protected"])
app.include_router(sign.router, prefix="/sign", tags=["Signing"])
app.include_router(profile.router, prefix="/user", tags=["User Profile"])
app.include_router(invitation.router, prefix="/invitations", tags=["Invitations"])

# API key authenticated routes (external API)
app.include_router(api_router)


@app.get("/", tags=["Health"])
def health_check():
    logger.info("Health check requested")
    return {"message": "eSign API is up and running"}