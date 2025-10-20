# ===============================
# 📄 backend/config.py
# ===============================

import os
from pathlib import Path
from dotenv import load_dotenv

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# ===============================
# 🔍 Robust .env loader
# ===============================
# Will search both backend/ and project root (/srv)
env_paths = [
    Path(__file__).resolve().parent / ".env.local",
    Path(__file__).resolve().parent.parent / ".env.local",
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment file: {env_path}")
        break
else:
    print("⚠️ Warning: .env.local not found in backend or project root.")

# ===============================
# 🌍 Environment Configuration
# ===============================
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

# ===============================
# ⚙️ Feature Toggles
# ===============================
ENABLE_GLYPH_LOGGING = os.getenv("ENABLE_GLYPH_LOGGING", "").lower()
if ENABLE_GLYPH_LOGGING == "":
    ENABLE_GLYPH_LOGGING = True  # default if not set in env
else:
    ENABLE_GLYPH_LOGGING = ENABLE_GLYPH_LOGGING == "true"

GW_ENABLED = os.getenv("GW_ENABLED", "").lower()
if GW_ENABLED == "":
    GW_ENABLED = True
else:
    GW_ENABLED = GW_ENABLED == "true"

GLYPH_API_BASE_URL = os.getenv("GLYPH_API_BASE_URL", "http://localhost:8000")

SPE_AUTO_FUSE = os.getenv("SPE_AUTO_FUSE", "false").lower() == "true"

# ===============================
# ⚛️ QQC Kernel Configuration
# ===============================
import yaml

def load_qqc_config(path=None):
    """
    Loads and merges QQC kernel configuration from YAML file,
    environment overrides, and runtime defaults.
    """
    cfg_path = path or QQC_CONFIG_PATH
    with open(cfg_path, "r") as f:
        cfg = yaml.safe_load(f) or {}

    cfg["mode"] = os.getenv("QQC_MODE", cfg.get("mode", "resonant"))
    cfg["env"] = ENV
    cfg["auto_start"] = os.getenv("QQC_AUTO_START", "false").lower() == "true"
    return cfg

QQC_CONFIG_PATH = os.getenv(
    "QQC_CONFIG_PATH",
    "backend/QQC/qqc_kernel_v2_config.yaml"
)

QQC_MODE = os.getenv("QQC_MODE", "resonant").lower()
QQC_AUTO_START = os.getenv("QQC_AUTO_START", "true").lower() == "true"