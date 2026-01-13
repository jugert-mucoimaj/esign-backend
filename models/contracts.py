import uuid
from sqlalchemy import Column, String, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.base import Base, POSTGRESQL_SCHEMA

class Contracts(Base):
    __tablename__ = "contracts"
    __table_args__ = {"schema": POSTGRESQL_SCHEMA}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    contract_name = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationship to associated contract parties
    parties = relationship("ContractParty", back_populates="contract", cascade="all, delete-orphan")


class ContractParty(Base):
    __tablename__ = "contract_parties"
    __table_args__ = {"schema": POSTGRESQL_SCHEMA}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    contract_id = Column(UUID(as_uuid=True), ForeignKey(f"{POSTGRESQL_SCHEMA}.contracts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("esign.users.id", ondelete="CASCADE"), nullable=False)
    # Optionally store the signature for this user in the contract context.
    signature_id = Column(UUID(as_uuid=True), ForeignKey(f"{POSTGRESQL_SCHEMA}.signatures.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    contract = relationship("Contracts", back_populates="parties")
    user = relationship("User")
    signature = relationship("Signature")
