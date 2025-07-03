import os
import json
from pathlib import Path
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from datetime import datetime

# Load .env for master key
load_dotenv()
KEVIN_MASTER_KEY = os.getenv("KEVIN_MASTER_KEY", "")
AION_VAULT_KEY = os.getenv("AION_VAULT_KEY", "")

if not AION_VAULT_KEY:
    raise ValueError("Missing AION_VAULT_KEY in environment.")

FERNET = Fernet(AION_VAULT_KEY)
VAULT_FILE = Path("backend/data/privacy_vault.json")

class PrivacyVault:
    """
    PrivacyVault is responsible for managing encrypted memory, secure module states,
    and privileged access by Kevin Robinson.
    """

    def __init__(self):
        self._vault = {}
        self._load()

    def _load(self):
        if VAULT_FILE.exists():
            try:
                encrypted = VAULT_FILE.read_bytes()
                decrypted = FERNET.decrypt(encrypted).decode("utf-8")
                self._vault = json.loads(decrypted)
            except Exception as e:
                print(f"⚠️ Failed to decrypt vault: {e}")
                self._vault = {}

    def _save(self):
        try:
            raw = json.dumps(self._vault, indent=2)
            encrypted = FERNET.encrypt(raw.encode("utf-8"))
            VAULT_FILE.write_bytes(encrypted)
        except Exception as e:
            print(f"⚠️ Vault save failed: {e}")

    def store(self, key: str, value: str):
        self._vault[key] = {
            "value": value,
            "timestamp": datetime.utcnow().isoformat()
        }
        self._save()
        print(f"🔐 Stored secret key: {key}")

    def retrieve(self, key: str) -> str | None:
        item = self._vault.get(key)
        return item["value"] if item else None

    def delete(self, key: str) -> bool:
        if key in self._vault:
            del self._vault[key]
            self._save()
            print(f"🗑️ Deleted key: {key}")
            return True
        return False

    def has_access(self, provided_key: str) -> bool:
        return provided_key == KEVIN_MASTER_KEY

    def list_keys(self):
        return list(self._vault.keys())

    def export_debug(self):
        """For debugging – prints decrypted vault contents"""
        return self._vault