# drop_tables.py
from models import Base, engine
from sqlalchemy import MetaData

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# Create a metadata object to manage the database schema
metadata = MetaData()

# Reflect the tables
Base.metadata.drop_all(bind=engine)

