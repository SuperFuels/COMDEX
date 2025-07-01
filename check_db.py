import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

if not DATABASE_URL:
    print("Error: SQLALCHEMY_DATABASE_URL environment variable not set.")
    exit(1)

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT NOW();"))
        current_time = result.scalar()
        print(f"Successfully connected to database. Current time: {current_time}")
except Exception as e:
    print(f"Failed to connect to the database: {e}")
