import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from database import get_db
from models.user import User
from models.contract_invitation import ContractInvitation, InvitationStatus
from utils.auth import get_current_user

router = APIRouter()


# --- Schemas ---

class InvitationCreate(BaseModel):
    receiver_email: EmailStr
    message: Optional[str] = None


class InvitationResponse(BaseModel):
    id: uuid.UUID
    sender_id: uuid.UUID
    sender_name: str
    sender_email: str
    receiver_id: uuid.UUID
    receiver_name: str
    receiver_email: str
    message: Optional[str]
    status: str
    created_at: datetime
    responded_at: Optional[datetime]

    class Config:
        from_attributes = True


class InvitationListResponse(BaseModel):
    sent: List[InvitationResponse]
    received: List[InvitationResponse]


# --- Helper ---

def invitation_to_response(invitation: ContractInvitation) -> InvitationResponse:
    return InvitationResponse(
        id=invitation.id,
        sender_id=invitation.sender_id,
        sender_name=f"{invitation.sender.first_name} {invitation.sender.last_name}",
        sender_email=invitation.sender.email,
        receiver_id=invitation.receiver_id,
        receiver_name=f"{invitation.receiver.first_name} {invitation.receiver.last_name}",
        receiver_email=invitation.receiver.email,
        message=invitation.message,
        status=invitation.status.value,
        created_at=invitation.created_at,
        responded_at=invitation.responded_at
    )


# --- Endpoints ---

@router.post("/", response_model=InvitationResponse)
async def create_invitation(
    data: InvitationCreate,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a contract invitation to another user."""
    # Find receiver by email
    result = await db.execute(select(User).where(User.email == data.receiver_email))
    receiver = result.scalars().first()

    if not receiver:
        raise HTTPException(status_code=404, detail="User not found")

    if receiver.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot send invitation to yourself")

    # Check for existing pending invitation
    existing = await db.execute(
        select(ContractInvitation).where(
            ContractInvitation.sender_id == user_id,
            ContractInvitation.receiver_id == receiver.id,
            ContractInvitation.status == InvitationStatus.PENDING
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Pending invitation already exists")

    invitation = ContractInvitation(
        sender_id=user_id,
        receiver_id=receiver.id,
        message=data.message
    )
    db.add(invitation)
    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(ContractInvitation)
        .options(selectinload(ContractInvitation.sender), selectinload(ContractInvitation.receiver))
        .where(ContractInvitation.id == invitation.id)
    )
    invitation = result.scalars().first()

    return invitation_to_response(invitation)


@router.get("/", response_model=InvitationListResponse)
async def list_invitations(
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all sent and received invitations."""
    # Sent invitations
    sent_result = await db.execute(
        select(ContractInvitation)
        .options(selectinload(ContractInvitation.sender), selectinload(ContractInvitation.receiver))
        .where(ContractInvitation.sender_id == user_id)
        .order_by(ContractInvitation.created_at.desc())
    )
    sent = [invitation_to_response(inv) for inv in sent_result.scalars().all()]

    # Received invitations
    received_result = await db.execute(
        select(ContractInvitation)
        .options(selectinload(ContractInvitation.sender), selectinload(ContractInvitation.receiver))
        .where(ContractInvitation.receiver_id == user_id)
        .order_by(ContractInvitation.created_at.desc())
    )
    received = [invitation_to_response(inv) for inv in received_result.scalars().all()]

    return InvitationListResponse(sent=sent, received=received)


@router.get("/pending", response_model=List[InvitationResponse])
async def list_pending_invitations(
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List pending invitations received by the current user."""
    result = await db.execute(
        select(ContractInvitation)
        .options(selectinload(ContractInvitation.sender), selectinload(ContractInvitation.receiver))
        .where(
            ContractInvitation.receiver_id == user_id,
            ContractInvitation.status == InvitationStatus.PENDING
        )
        .order_by(ContractInvitation.created_at.desc())
    )
    invitations = [invitation_to_response(inv) for inv in result.scalars().all()]
    return invitations


@router.post("/{invitation_id}/accept", response_model=InvitationResponse)
async def accept_invitation(
    invitation_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Accept a contract invitation."""
    result = await db.execute(
        select(ContractInvitation)
        .options(selectinload(ContractInvitation.sender), selectinload(ContractInvitation.receiver))
        .where(ContractInvitation.id == invitation_id)
    )
    invitation = result.scalars().first()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.receiver_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to accept this invitation")

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Invitation already {invitation.status.value}")

    invitation.status = InvitationStatus.ACCEPTED
    invitation.responded_at = datetime.utcnow()
    await db.commit()
    await db.refresh(invitation)

    return invitation_to_response(invitation)


@router.post("/{invitation_id}/reject", response_model=InvitationResponse)
async def reject_invitation(
    invitation_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reject a contract invitation."""
    result = await db.execute(
        select(ContractInvitation)
        .options(selectinload(ContractInvitation.sender), selectinload(ContractInvitation.receiver))
        .where(ContractInvitation.id == invitation_id)
    )
    invitation = result.scalars().first()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.receiver_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to reject this invitation")

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Invitation already {invitation.status.value}")

    invitation.status = InvitationStatus.REJECTED
    invitation.responded_at = datetime.utcnow()
    await db.commit()
    await db.refresh(invitation)

    return invitation_to_response(invitation)


@router.delete("/{invitation_id}")
async def cancel_invitation(
    invitation_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a sent invitation (sender only)."""
    result = await db.execute(
        select(ContractInvitation).where(ContractInvitation.id == invitation_id)
    )
    invitation = result.scalars().first()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.sender_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this invitation")

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Can only cancel pending invitations")

    await db.delete(invitation)
    await db.commit()

    return {"message": "Invitation cancelled successfully"}