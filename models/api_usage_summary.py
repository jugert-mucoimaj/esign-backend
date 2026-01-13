import uuid
from sqlalchemy import Column, Date, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from models.api_key import API_SCHEMA
from models.base import Base
from sqlalchemy.dialects.postgresql import JSONB, UUID

class ApiUsageSummary(Base):
    __tablename__ = "api_usage_summary"
    __table_args__ = {"schema": API_SCHEMA}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_management.api_keys.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    year_week = Column(String, nullable=False, index=True)
    year_month = Column(String, nullable=False, index=True)
    total_calls = Column(Integer, nullable=False, default=0, index=True)  # Indexed for performance
    cumulative_calls = Column(Integer, nullable=False, default=0)  # New: Running total of API calls
    usage_data = Column(JSONB, nullable=False, default={})

    api_key = relationship("ApiKey", back_populates="usage_summaries")
