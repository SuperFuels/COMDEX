# backend/config.py

import os

# Cloud Run mounts your Cloud SQL socket under /cloudsql
DB_USER                   = os.getenv("DB_USER", "")
DB_PASS                   = os.getenv("DB_PASS", "")
DB_NAME                   = os.getenv("DB_NAME", "")
INSTANCE_CONNECTION_NAME  = os.getenv("INSTANCE_CONNECTION_NAME", "")

# Ensure we have everything we need
if not all([DB_USER, DB_PASS, DB_NAME, INSTANCE_CONNECTION_NAME]):
    raise RuntimeError(
        "Missing one of DB_USER, DB_PASS, DB_NAME or INSTANCE_CONNECTION_NAME in environment"
    )

# Build the socket-based SQLAlchemy URL
SQLALCHEMY_DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@/{DB_NAME}"
    f"?host=/cloudsql/{INSTANCE_CONNECTION_NAME}"
)

