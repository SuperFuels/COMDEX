# backend/database.py

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# Choose DATABASE_URL from env, fallback to SQLite (for local development)
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URL") or "sqlite:///./dev.db"

# Log the selected database URL (sanitized for safety)
logging.basicConfig(level=logging.INFO)
sanitized_url = DATABASE_URL.replace(os.getenv("Wn8smx123", "*****"), "*****")  # optional masking
logging.info(f"🔍 Using DATABASE_URL = {DATABASE_URL}")

# Special connect_args if SQLite is being used
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Create SQLAlchemy engine (disable pooling for serverless like Cloud Run)
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    poolclass=NullPool,
    pool_pre_ping=True,
)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI or CLI use
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()