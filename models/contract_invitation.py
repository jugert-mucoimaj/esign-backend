# models/contract_invitation.py
import uuid
import enum
from sqlalchemy import Column, ForeignKey, TIMESTAMP, func, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.base import Base, POSTGRESQL_SCHEMA


class InvitationStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ContractInvitation(Base):
    __tablename__ = "contract_invitations"
    __table_args__ = {"schema": POSTGRESQL_SCHEMA}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("esign.users.id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(UUID(as_uuid=True), ForeignKey("esign.users.id", ondelete="CASCADE"), nullable=False)
    message = Column(Text, nullable=True)  # Optional message from sender
    status = Column(Enum(InvitationStatus), nullable=False, default=InvitationStatus.PENDING)
    created_at = Column(TIMESTAMP, server_default=func.now())
    responded_at = Column(TIMESTAMP, nullable=True)  # When accepted/rejected

    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])