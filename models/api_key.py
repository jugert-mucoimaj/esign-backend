import uuid
from sqlalchemy import Column, Text, String, ForeignKey, TIMESTAMP, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.base import Base, POSTGRESQL_SCHEMA  # Import schema from base

API_SCHEMA = "api_management"

class ApiKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = {"schema": API_SCHEMA}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey(f"{POSTGRESQL_SCHEMA}.users.id", ondelete="CASCADE"), nullable=False)
    api_key = Column(Text, unique=True, nullable=False, index=True)
    tier = Column(String, nullable=False, default="starter")
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    logs = relationship("ApiLog", back_populates="api_key", cascade="all, delete")
    usage_summaries = relationship("ApiUsageSummary", back_populates="api_key", cascade="all, delete")
    user = relationship("User", back_populates="api_keys")  # Keep it as a string to avoid circular import
