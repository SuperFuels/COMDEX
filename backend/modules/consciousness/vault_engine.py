import os
from dotenv import load_dotenv

# Load .env file to get KEVIN_MASTER_KEY
load_dotenv()
KEVIN_MASTER_KEY = os.getenv("KEVIN_MASTER_KEY", "")

class PrivacyVault:
    """
    PrivacyVault is responsible for managing private or sensitive data,
    such as encrypted memories, access controls, or secure storage.
    """

    def __init__(self):
        # Initialize vault storage (in-memory for now)
        self._vault = {}

    def store(self, key: str, value: str) -> None:
        """
        Store a value securely under a given key.
        """
        # For now, store directly; later can add encryption
        self._vault[key] = value

    def retrieve(self, key: str) -> str | None:
        """
        Retrieve a stored value by key.
        """
        return self._vault.get(key)

    def delete(self, key: str) -> bool:
        """
        Delete a stored value by key.
        Returns True if deleted, False if key not found.
        """
        if key in self._vault:
            del self._vault[key]
            return True
        return False

    def has_access(self, key: str) -> bool:
        """
        Check if the provided key matches the master override key.
        Used to validate privileged access by Kevin Robinson.
        """
        return key == KEVIN_MASTER_KEY