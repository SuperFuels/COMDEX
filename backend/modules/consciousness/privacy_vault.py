import os
import json
from pathlib import Path
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from datetime import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# Load .env if available
load_dotenv()

VAULT_FILE = Path("backend/data/privacy_vault.json")

def get_vault_key():
    key = os.getenv("AION_VAULT_KEY", "")
    if not key:
        print("⚠️ Warning: AION_VAULT_KEY not found. Vault will remain locked.")
    return key

def get_master_key():
    return os.getenv("KEVIN_MASTER_KEY", "")

class PrivacyVault:
    """
    PrivacyVault is responsible for managing encrypted memory, secure module states,
    and privileged access by Kevin Robinson.
    """

    def __init__(self):
        self._vault = {}
        self._fernet = None
        self._load()

    def _load(self):
        key = get_vault_key()
        if not key:
            return
        try:
            self._fernet = Fernet(key)
            if VAULT_FILE.exists():
                encrypted = VAULT_FILE.read_bytes()
                decrypted = self._fernet.decrypt(encrypted).decode("utf-8")
                self._vault = json.loads(decrypted)
        except Exception as e:
            print(f"⚠️ Failed to load/decrypt vault: {e}")
            self._vault = {}

    def _save(self):
        if not self._fernet:
            print("⚠️ Cannot save: AION_VAULT_KEY not set.")
            return
        try:
            raw = json.dumps(self._vault, indent=2)
            encrypted = self._fernet.encrypt(raw.encode("utf-8"))
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
        return provided_key == get_master_key()

    def list_keys(self):
        return list(self._vault.keys())

    def export_debug(self):
        """For debugging - prints decrypted vault contents"""
        return self._vault