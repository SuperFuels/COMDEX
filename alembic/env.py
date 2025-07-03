# alembic/env.py

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ✅ Add project root to PYTHONPATH for clean imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ✅ Import Base and models to populate metadata
from backend.database import Base
from backend.models.dream import Dream  # This ensures 'dreams' table is picked up

# Load Alembic config
config = context.config

# Enable logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate
target_metadata = Base.metadata

# ✅ Load DB URL from ENV or fallback to config
def get_database_url():
    return os.getenv(
        "DATABASE_URL",
        os.getenv("SQLALCHEMY_DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    )


def run_migrations_offline() -> None:
    """Run migrations without DB connection (offline mode)."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with live DB connection (online mode)."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()