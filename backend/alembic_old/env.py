from __future__ import with_statement
import sys
import os
from alembic import context
from sqlalchemy import create_engine
from sqlalchemy import pool
from sqlalchemy.ext.declarative import declarative_base
from logging.config import fileConfig

# Import your models here
# Ensure this points to the correct location of your models, e.g., from models.user import Base
from models import Base  # Ensure this points to the correct module where Base is defined

# this is the Alembic Config object, which provides access to the values
# within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set up the target metadata for "autogenerate" support
# Make sure this points to the metadata object
target_metadata = Base.metadata

# Set up the database URL from alembic.ini
sqlalchemy_url = config.get_main_option("sqlalchemy.url")

# Create an engine with the database URL
engine = create_engine(sqlalchemy_url, poolclass=pool.NullPool)

# Run migrations in 'offline' mode
def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = sqlalchemy_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

# Run migrations in 'online' mode
def run_migrations_online():
    """Run migrations in 'online' mode."""
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

# Determine if Alembic is running in offline or online mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

