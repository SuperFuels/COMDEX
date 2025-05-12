from __future__ import with_statement
import sys
import os
from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.ext.declarative import declarative_base
from logging.config import fileConfig

# Add this import to link to your models and Base
from models import Base  # This should import from where you define your models

config = context.config
fileConfig(config.config_file_name)

# Set up the target metadata for autogenerate support
target_metadata = Base.metadata  # This is where Base is defined in your models.py

sqlalchemy_url = config.get_main_option("sqlalchemy.url")
engine = create_engine(sqlalchemy_url, poolclass=pool.NullPool)

def run_migrations_offline():
    url = sqlalchemy_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

