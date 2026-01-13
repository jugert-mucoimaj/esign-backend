import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text
from alembic import context
from database import DATABASE_URL  # Import database URL
from models import *

# PostgreSQL Schema
POSTGRESQL_SCHEMA = "esign"

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the metadata target for autogenerate support
target_metadata = Base.metadata

# Create async engine
engine = create_async_engine(DATABASE_URL, future=True)


def ensure_schema_exists(connection):
    """Ensure that the PostgreSQL schema exists before applying migrations."""
    connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {POSTGRESQL_SCHEMA}"))


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(ensure_schema_exists)

        def do_run_migrations(sync_conn):
            # Configure the context with the current connection and schema
            context.configure(
                connection=sync_conn,
                target_metadata=target_metadata,
                include_schemas=True,  # ✅ Ensure schema is included in migrations
            )

            # Start a transaction and run migrations
            with context.begin_transaction():
                context.run_migrations()

        # Execute the synchronous migration function within the async connection
        await connection.run_sync(do_run_migrations)


def run_migrations() -> None:
    """Run Alembic migrations in the correct mode."""
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        asyncio.run(run_migrations_online())


run_migrations()
