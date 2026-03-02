# backend/database.py

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# -----------------------------------------------------------------------------
# Local device default:
# - uses SQLite unless DATABASE_URL / SQLALCHEMY_DATABASE_URL is explicitly set
# - this lets the full project boot locally without G Cloud / Cloud SQL
#
# G Cloud setup:
# - to reactivate G Cloud later, set ENV=production plus a postgres/cloudsql URL
# - then you can delete this comment block and reuse the old prod env values
# -----------------------------------------------------------------------------
DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("SQLALCHEMY_DATABASE_URL")
    or "sqlite:///./dev.db"
)

# Log the selected database URL safely
logging.basicConfig(level=logging.INFO)

sanitized_url = DATABASE_URL
db_pass = os.getenv("DB_PASS")
if db_pass:
    sanitized_url = sanitized_url.replace(db_pass, "*****")

logging.info(f"🔍 Using DATABASE_URL = {sanitized_url}")

# SQLite needs check_same_thread disabled
is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

# NullPool is fine for local and also keeps prior Cloud Run behaviour simple
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    poolclass=NullPool,
    pool_pre_ping=True,
)

# Create a session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI or CLI use
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()