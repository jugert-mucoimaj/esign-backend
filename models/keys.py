import uuid
from sqlalchemy import Column, Text, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.base import Base, POSTGRESQL_SCHEMA

class KeyPair(Base):
    __tablename__ = "keys"
    __table_args__ = {"schema": POSTGRESQL_SCHEMA}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("esign.users.id", ondelete="CASCADE"), unique=True, nullable=False)
    public_key = Column(Text, nullable=False)  # Changed from String to Text
    private_key = Column(Text, nullable=False)  # Changed from String to Text
    created_at = Column(TIMESTAMP, server_default=func.now())  # Added timestamp

    user = relationship("User", back_populates="key_pair")
