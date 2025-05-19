# backend/config.py

import os

# Load .env locally if present (for dev)
if os.getenv("ENV", "").lower() != "production":
    from dotenv import load_dotenv
    load_dotenv()

# Basic DB credentials
DB_USER   = os.getenv("DB_USER", "")
DB_PASS   = os.getenv("DB_PASS", "")
DB_NAME   = os.getenv("DB_NAME", "")
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME", "")

# If you have a Cloud SQL socket, use it…
if INSTANCE_CONNECTION_NAME:
    SQLALCHEMY_DATABASE_URL = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@/{DB_NAME}"
        f"?host=/cloudsql/{INSTANCE_CONNECTION_NAME}"
    )
else:
    # Otherwise allow override via DATABASE_URL, or default to localhost
    SQLALCHEMY_DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"postgresql://{DB_USER}:{DB_PASS}@localhost:5432/{DB_NAME}"
    )

