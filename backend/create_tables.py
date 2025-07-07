# backend/create_tables.py

import os
import logging
from sqlalchemy import create_engine

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# Import your shared Base and engine config
from backend.database import Base
# Import every model module so Base.metadata knows about them
import models.user
import models.product
import models.deal
import models.contract

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use the same DATABASE_URL that your app uses
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://comdex:Wn8smx123@localhost:5432/comdex"
)

# Create the engine
engine = create_engine(DATABASE_URL, echo=True)

try:
    # Create all tables defined on Base.metadata
    Base.metadata.create_all(bind=engine)
    logger.info("✅ All tables (including contracts) created/updated successfully.")
except Exception as e:
    logger.error(f"❌ Error during table creation: {e}")

