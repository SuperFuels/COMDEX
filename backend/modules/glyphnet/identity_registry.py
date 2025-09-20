import logging
import threading
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec

logger = logging.getLogger(__name__)

# In-memory identity key store (identity → PEM public key)
_identity_keys: Dict[str, str] = {}
_identity_tokens: Dict[str, str] = {}  # Identity → token mapping for validation
_lock = threading.Lock()


def register_identity(identity: str, public_key_pem: str, token: Optional[str] = None) -> bool:
    """
    Register a new identity with its public key in PEM format.
    Optionally associate an authentication token for validation.
    """
    try:
        key = serialization.load_pem_public_key(public_key_pem.encode())
        if not isinstance(key, (rsa.RSAPublicKey, ec.EllipticCurvePublicKey)):
            logger.error(f"[IdentityRegistry] ❌ Unsupported key type for {identity}")
            return False

        with _lock:
            _identity_keys[identity] = public_key_pem
            if token:
                _identity_tokens[identity] = token
        logger.info(f"[IdentityRegistry] ✅ Registered identity: {identity}")

        # TODO: Persist key/token securely in GlyphVault
        return True
    except Exception as e:
        logger.error(f"[IdentityRegistry] Failed to register {identity}: {e}")
        return False


def validate_agent_token(token: str) -> bool:
    """
    Validate an agent token against the identity registry.
    """
    with _lock:
        for identity, stored_token in _identity_tokens.items():
            if stored_token == token:
                logger.debug(f"[IdentityRegistry] ✅ Token validated for identity: {identity}")
                return True
    logger.warning(f"[IdentityRegistry] ❌ Invalid token attempted: {token}")
    return False


def validate_identity_token(identity: str, token: str) -> bool:
    """
    Validate that a specific token belongs to the given identity.
    """
    with _lock:
        stored = _identity_tokens.get(identity)
    if stored and stored == token:
        logger.debug(f"[IdentityRegistry] ✅ Token validated for {identity}")
        return True
    logger.warning(f"[IdentityRegistry] ❌ Token validation failed for {identity}")
    return False


def get_public_key_for_target(identity: str):
    """
    Retrieve the loaded public key object for a given identity.
    Returns None if not found or failed to load.
    """
    with _lock:
        pem = _identity_keys.get(identity)

    if not pem:
        logger.warning(f"[IdentityRegistry] ⚠️ No public key found for identity: {identity}")
        return None

    try:
        return serialization.load_pem_public_key(pem.encode())
    except Exception as e:
        logger.error(f"[IdentityRegistry] Error loading public key for {identity}: {e}")
        return None


def get_registered_token(identity: str) -> Optional[str]:
    """
    Retrieve the registered token for a given identity.
    """
    with _lock:
        return _identity_tokens.get(identity)


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
            logger.info(f"[IdentityRegistry] 🗑️ Removed identity: {identity}")
            # TODO: Remove from Vault/secure storage
            return True

    logger.warning(f"[IdentityRegistry] ⚠️ Attempted to remove unknown identity: {identity}")
    return False


def export_registry_state() -> Dict[str, Any]:
    """
    Export a snapshot of the registry (keys + tokens).
    Safe for persistence.
    """
    with _lock:
        return {
            "keys": _identity_keys.copy(),
            "tokens": _identity_tokens.copy(),
        }


def import_registry_state(state: Dict[str, Any]) -> None:
    """
    Import a snapshot into the registry (overwrites conflicts).
    Useful for restoring from persistence.
    """
    with _lock:
        keys = state.get("keys", {})
        tokens = state.get("tokens", {})
        _identity_keys.update(keys)
        _identity_tokens.update(tokens)
    logger.info(f"[IdentityRegistry] 🔄 Imported registry state with {len(keys)} keys, {len(tokens)} tokens")