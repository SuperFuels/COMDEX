from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Import the socket-based URL from config
from .config import SQLALCHEMY_DATABASE_URL

# Create engine for PostgreSQL via Cloud SQL Unix socket
# echo=True to log SQL statements; pool_pre_ping=True to ensure connections
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=True,
    pool_pre_ping=True
)

# Base class for models
Base = declarative_base()

# Create a session maker for database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Dependency for FastAPI to get DB session
# Usage in path operations:
#   def endpoint(db: Session = Depends(get_db)):
#       ...
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

