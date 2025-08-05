import logging
import threading
from typing import Optional, Dict
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec

logger = logging.getLogger(__name__)

# In-memory identity key store (identity → PEM public key)
_identity_keys: Dict[str, str] = {}
_identity_tokens: Dict[str, str] = {}  # ✅ Added: Identity → token mapping for validation
_lock = threading.Lock()


def register_identity(identity: str, public_key_pem: str, token: Optional[str] = None) -> bool:
    """
    Register a new identity with its public key in PEM format.
    Optionally associate an authentication token for validation.

    Args:
        identity (str): The unique identity string.
        public_key_pem (str): The PEM-formatted public key string.
        token (Optional[str]): Optional agent authentication token.

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
            if token:
                _identity_tokens[identity] = token  # ✅ Store token if provided
        logger.info(f"[IdentityRegistry] Registered identity: {identity}")

        # TODO: Persist key/token securely in GlyphVault
        return True
    except Exception as e:
        logger.error(f"[IdentityRegistry] Failed to register {identity}: {e}")
        return False


def validate_agent_token(token: str) -> bool:
    """
    Validate an agent token against the identity registry.

    Args:
        token (str): The token string to validate.

    Returns:
        bool: True if token is associated with a registered identity, False otherwise.
    """
    with _lock:
        for identity, stored_token in _identity_tokens.items():
            if stored_token == token:
                logger.debug(f"[IdentityRegistry] ✅ Token validated for identity: {identity}")
                return True
    logger.warning(f"[IdentityRegistry] ❌ Invalid token attempted: {token}")
    return False


def get_public_key_for_target(identity: str) -> Optional[serialization.PublicFormat]:
    """
    Retrieve the loaded public key object for a given identity.
    Returns None if not found or failed to load.
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
    """
    with _lock:
        return _identity_keys.copy()


def remove_identity(identity: str) -> bool:
    """
    Remove a registered identity, its key, and its token.
    Useful for key revocation.
    """
    with _lock:
        removed = False
        if identity in _identity_keys:
            del _identity_keys[identity]
            removed = True
        if identity in _identity_tokens:
            del _identity_tokens[identity]
            removed = True

        if removed:
            logger.info(f"[IdentityRegistry] Removed identity: {identity}")
            # TODO: Remove from Vault/secure storage
            return True

    logger.warning(f"[IdentityRegistry] Attempted to remove unknown identity: {identity}")
    return False