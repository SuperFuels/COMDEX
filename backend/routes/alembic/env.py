from __future__ import with_statement
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import your model's Base and MetaData object here
from models import Base  # Ensure you import the correct Base from where your models are defined

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers in your config file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here
# For 'autogenerate' support
target_metadata = Base.metadata  # Make sure to use the correct metadata object

# Function to run migrations in 'offline' mode
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# Function to run migrations in 'online' mode
def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
    
        with context.begin_transaction():
            context.run_migrations()


# Run migrations in the appropriate mode based on the configuration
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

