import os
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

# Pull from ENV first; then from your config module; else default to SQLite
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    os.getenv("SQLALCHEMY_DATABASE_URL", "sqlite:///./dev.db")
)

# Log which database URL we’re actually using
logging.basicConfig(level=logging.INFO)
logging.info(f"🔍 SQLALCHEMY_DATABASE_URL = {DATABASE_URL}")

# If using SQLite, disable the same-thread check
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

# 1) Engine & session factory
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    poolclass=NullPool,     # no connection pooling on Cloud Run
    pool_pre_ping=True,     # detect stale connections
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# 2) Base class for all models
Base = declarative_base()

# 3) Dependency for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()