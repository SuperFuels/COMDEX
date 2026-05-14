import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ─── 0) load .env early ────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

# ─── 1) ensure your project root is on PYTHONPATH ──────────────────────
#    so we can database, backend.models, etc.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ─── 2) Alembic Config object ─────────────────────────────────────────
config = context.config

# ─── 3) allow env var to override sqlalchemy.url ───────────────────────
if os.getenv("SQLALCHEMY_DATABASE_URL"):
    config.set_main_option("sqlalchemy.url", os.getenv("SQLALCHEMY_DATABASE_URL"))

# ─── 4) Logging setup ─────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ─── 5) import your MetaData ──────────────────────────────────────────
database import Base  # noqa: E402
target_metadata = Base.metadata

# ─── 6) import all your models so Alembic sees them ────────────────────
models.user      # noqa: E402
models.product   # noqa: E402
models.deal      # noqa: E402
models.contract  # noqa: E402

# ─── Offline migrations ────────────────────────────────────────────────
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

# ─── Online migrations ─────────────────────────────────────────────────
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

# ─── Entrypoint ────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()