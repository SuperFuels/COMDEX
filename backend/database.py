# backend/database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# pull in the socket- or localhost-URL from config.py
from .config import SQLALCHEMY_DATABASE_URL

# 1) engine & session factory
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 2) Base class for your models
Base = declarative_base()

# 3) import all of your models so they register with Base
#    (adjust these to match your actual model filenames)
from .models.user    import User
from .models.product import Product
from .models.deal    import Deal
from .models.contract import Contract
# …and any others

# 4) auto-create missing tables in your Cloud SQL database
Base.metadata.create_all(bind=engine)


# 5) FastAPI dependency to get a session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

