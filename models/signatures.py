import uuid
from sqlalchemy import Column, Text, ForeignKey, LargeBinary, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.base import Base, POSTGRESQL_SCHEMA

class Signature(Base):
    __tablename__ = "signatures"
    __table_args__ = {"schema": POSTGRESQL_SCHEMA}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("esign.users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(Text, nullable=False)
    signature = Column(Text, nullable=False)  # Changed from String to Text
    content = Column(LargeBinary, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())  # Added timestamp

    user = relationship("User", back_populates="signatures")
