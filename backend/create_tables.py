import os
import logging
from sqlalchemy import create_engine
from models import Base, User, Deal, Product  # Import all necessary models

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PostgreSQL URL (ensure this matches your actual connection details)
DATABASE_URL = "postgresql://comdex_user:your_password@localhost/comdex"  # Update this with actual credentials

# Setup the engine for PostgreSQL (not SQLite)
engine = create_engine(DATABASE_URL, echo=True)

try:
    # Create all tables in the database (User, Deal, Product, etc.)
    Base.metadata.create_all(engine)
    logger.info("Tables created successfully.")
except Exception as e:
    logger.error(f"Error during table creation: {str(e)}")

