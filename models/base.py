from sqlalchemy.orm import DeclarativeBase

POSTGRESQL_SCHEMA = "esign"

class Base(DeclarativeBase):
    __abstract__ = True
    __table_args__ = {"schema": POSTGRESQL_SCHEMA}
