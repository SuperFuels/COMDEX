import os
from dotenv import load_dotenv

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

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
    DB_USER                  = os.getenv("DB_USER")
    DB_PASS                  = os.getenv("DB_PASS")
    DB_NAME                  = os.getenv("DB_NAME")
    INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME")
    SQLALCHEMY_DATABASE_URL  = os.getenv("SQLALCHEMY_DATABASE_URL") or (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@/{DB_NAME}"
        f"?host=/cloudsql/{INSTANCE_CONNECTION_NAME}"
    )

# ✅ Glyph Logging Toggle (env override, defaults to True)
ENABLE_GLYPH_LOGGING = os.getenv("ENABLE_GLYPH_LOGGING", "").lower()
if ENABLE_GLYPH_LOGGING == "":
    ENABLE_GLYPH_LOGGING = True  # default if not set in env
else:
    ENABLE_GLYPH_LOGGING = ENABLE_GLYPH_LOGGING == "true"

# ✅ Glyph API base URL (used by glyph_api_client.py and runtime synthesis)
GLYPH_API_BASE_URL = os.getenv("GLYPH_API_BASE_URL", "http://localhost:8000")