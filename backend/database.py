from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# PostgreSQL URL - Update this with your actual PostgreSQL details
SQLALCHEMY_DATABASE_URL = "postgresql://comdex_user:your_password@localhost/comdex"  # Update your password and DB name

# Create engine for PostgreSQL (no need for connect_args in PostgreSQL)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,  # Connecting to PostgreSQL
    echo=True  # Set to True to see the SQL queries being executed, useful for debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ✅ Dependency for FastAPI to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

