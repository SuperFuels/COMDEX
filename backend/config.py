import os
from dotenv import load_dotenv

# 1) load .env if present
load_dotenv()

ENV = os.getenv("ENV", "").lower()

if ENV != "production":
    # local/dev: use SQLite (no external DB required)
    SQLALCHEMY_DATABASE_URL = os.getenv(
        "SQLALCHEMY_DATABASE_URL",
        "sqlite:///./dev.db"
    )
else:
    # prod: build from Cloud SQL socket (or override with env var)
    DB_USER                 = os.getenv("DB_USER")
    DB_PASS                 = os.getenv("DB_PASS")
    DB_NAME                 = os.getenv("DB_NAME")
    INSTANCE_CONNECTION_NAME= os.getenv("INSTANCE_CONNECTION_NAME")
    SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL") or (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@/{DB_NAME}"
        f"?host=/cloudsql/{INSTANCE_CONNECTION_NAME}"
    )
    