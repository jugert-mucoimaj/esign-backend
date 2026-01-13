import uuid
from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.api_key import API_SCHEMA
from models.base import Base

class ApiLog(Base):
    __tablename__ = "api_logs"
    __table_args__ = {"schema": API_SCHEMA}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_management.api_keys.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False, default=200)  # Added status code tracking
    timestamp = Column(TIMESTAMP, server_default=func.now())

    api_key = relationship("ApiKey", back_populates="logs")
