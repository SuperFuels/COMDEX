# drop_tables.py
from models import Base, engine
from sqlalchemy import MetaData

# Create a metadata object to manage the database schema
metadata = MetaData()

# Reflect the tables
Base.metadata.drop_all(bind=engine)

