import logging
import threading
from typing import Optional, Dict
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec

logger = logging.getLogger(__name__)

# In-memory identity key store (identity → PEM public key)
_identity_keys: Dict[str, str] = {}
_lock = threading.Lock()

def register_identity(identity: str, public_key_pem: str) -> bool:
    """
    Register a new identity with its public key in PEM format.
    Validates PEM format and key type.

    Args:
        identity (str): The unique identity string.
        public_key_pem (str): The PEM-formatted public key string.

    Returns:
        bool: True if registration successful, False otherwise.
    """
    try:
        key = serialization.load_pem_public_key(public_key_pem.encode())
        if not isinstance(key, (rsa.RSAPublicKey, ec.EllipticCurvePublicKey)):
            logger.error(f"[IdentityRegistry] Unsupported key type for {identity}")
            return False

        with _lock:
            _identity_keys[identity] = public_key_pem
        logger.info(f"[IdentityRegistry] Registered identity: {identity}")

        # TODO: Persist key to Vault or secure storage here

        return True
    except Exception as e:
        logger.error(f"[IdentityRegistry] Failed to register {identity}: {e}")
        return False

def get_public_key_for_target(identity: str) -> Optional[serialization.PublicFormat]:
    """
    Retrieve the loaded public key object for given identity.
    Returns None if not found or failed to load.

    Args:
        identity (str): The identity string.

    Returns:
        Optional[serialization.PublicFormat]: The public key object or None.
    """
    with _lock:
        pem = _identity_keys.get(identity)

    if not pem:
        logger.warning(f"[IdentityRegistry] No public key found for identity: {identity}")
        return None

    try:
        public_key = serialization.load_pem_public_key(pem.encode())
        return public_key
    except Exception as e:
        logger.error(f"[IdentityRegistry] Error loading public key for {identity}: {e}")
        return None

def list_registered_identities() -> Dict[str, str]:
    """
    Return a copy of all registered identities and their PEM keys.

    Returns:
        Dict[str, str]: Copy of identity → PEM key mapping.
    """
    with _lock:
        return _identity_keys.copy()

def remove_identity(identity: str) -> bool:
    """
    Remove a registered identity and its key.
    Useful for key revocation.

    Args:
        identity (str): The identity string.

    Returns:
        bool: True if removed, False if not found.
    """
    with _lock:
        if identity in _identity_keys:
            del _identity_keys[identity]
            logger.info(f"[IdentityRegistry] Removed identity: {identity}")
            # TODO: Remove from Vault or secure storage
            return True
    logger.warning(f"[IdentityRegistry] Attempted to remove unknown identity: {identity}")
    return False