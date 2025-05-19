# backend/database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import SQLALCHEMY_DATABASE_URL

# 1) Build your single engine from the socket‐based URL
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

# 2) Base for your models
Base = declarative_base()

# 3) Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    FastAPI dependency: yield a DB session, then close it.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

