import uuid
from sqlalchemy import Column, String, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.base import Base, POSTGRESQL_SCHEMA

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": POSTGRESQL_SCHEMA}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete")
    key_pair = relationship("KeyPair", back_populates="user", uselist=False, cascade="all, delete")
    signatures = relationship("Signature", back_populates="user", cascade="all, delete")
    encryption_salt = Column(LargeBinary, nullable=True)
