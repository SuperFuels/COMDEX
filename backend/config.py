# backend/config.py

import os

# Determine environment
ENV = os.getenv("ENV", "").lower()

# Load .env locally if not in production
if ENV != "production":
    from dotenv import load_dotenv
    load_dotenv()

# Basic DB credentials
DB_USER                  = os.getenv("DB_USER", "")
DB_PASS                  = os.getenv("DB_PASS", "")
DB_NAME                  = os.getenv("DB_NAME", "")
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME", "")

# Ensure we have everything we need for production
if ENV == "production":
    if not all([DB_USER, DB_PASS, DB_NAME, INSTANCE_CONNECTION_NAME]):
        raise RuntimeError(
            "Missing one of DB_USER, DB_PASS, DB_NAME or INSTANCE_CONNECTION_NAME in environment"
        )

# Build the SQLAlchemy URL based on the environment
if ENV != "production":
    # Local development fallback to localhost or override via DATABASE_URL
    SQLALCHEMY_DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"postgresql://{DB_USER}:{DB_PASS}@localhost:5432/{DB_NAME}"
    )
else:
    # Cloud Run / Cloud SQL over Unix socket
    SQLALCHEMY_DATABASE_URL = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@/{DB_NAME}"
        f"?host=/cloudsql/{INSTANCE_CONNECTION_NAME}"
    )

