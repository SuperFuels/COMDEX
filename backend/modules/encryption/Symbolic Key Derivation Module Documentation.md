Symbolic Key Derivation Module Documentation

Overview

The Symbolic Key Derivation system provides a secure, entropy-aware method to generate cryptographic keys based on symbolic parameters such as trust and emotion levels, timestamps, and optional seed phrases. It includes built-in protection against brute-force attacks through rate limiting and lockout mechanisms.

This system is designed for ephemeral key generation with a focus on symbolic AI contexts, ensuring keys are reproducible for the same inputs (when deterministic mode is enabled) and resilient against attack vectors.

⸻

Features
	•	Deterministic key derivation based on symbolic inputs
	•	Optional salt and nonce addition for randomness
	•	Key stretching for computational hardness
	•	Lockout and brute-force attempt tracking
	•	Runtime entropy integration for increased randomness
	•	Thread-safe internal state and metrics collection
	•	Key verification method for matching derived keys
	•	Centralized runtime metrics with counters for usage and security monitoring

⸻

API

Class: SymbolicKeyDerivation

derive_key(trust_level: float, emotion_level: float, timestamp: float, identity: Optional[str] = None, seed_phrase: Optional[str] = None, use_salt: bool = True, fixed_entropy: Optional[str] = None) -> Optional[bytes]

Derives a cryptographic key based on the provided symbolic parameters.
	•	trust_level: Numeric trust value (0.0–1.0)
	•	emotion_level: Numeric emotion value (0.0–1.0)
	•	timestamp: Unix timestamp (float)
	•	identity: Optional string ID used for rate limiting and lockout enforcement
	•	seed_phrase: Optional string to add extra seed input
	•	use_salt: Whether to add random salt and nonce (default True)
	•	fixed_entropy: Optional entropy string override (for deterministic keys)

Returns:
	•	A derived key as bytes, or None if derivation is blocked or fails.

Raises:
	•	Does not raise exceptions; returns None on failure or invalid inputs.

⸻

verify_key(key: bytes, trust_level: float, emotion_level: float, timestamp: float, identity: Optional[str] = None, seed_phrase: Optional[str] = None) -> bool

Verifies that a provided key matches the derivation from given parameters.

Returns:
	•	True if the key matches, False otherwise or if verification is blocked.

⸻

get_metrics_snapshot() -> Dict[str, int]

Returns a thread-safe snapshot dictionary of runtime metrics including:
	•	total_derivations
	•	successful_derivations
	•	failed_derivations
	•	lockouts_triggered
	•	entropy_failures
	•	suspicious_attempts

⸻

Usage Examples

from backend.modules.glyphnet.symbolic_key_derivation import symbolic_key_deriver

# Derive a key with symbolic parameters
key = symbolic_key_deriver.derive_key(
    trust_level=0.7,
    emotion_level=0.3,
    timestamp=1650000000,
    identity="user_session_123",
    seed_phrase="optional_seed"
)

if key:
    print("Derived key:", key.hex())
else:
    print("Key derivation failed or blocked.")

# Verify a key
valid = symbolic_key_deriver.verify_key(
    key,
    trust_level=0.7,
    emotion_level=0.3,
    timestamp=1650000000,
    identity="user_session_123",
    seed_phrase="optional_seed"
)
print("Key is valid:", valid)

# Fetch metrics for monitoring
metrics = symbolic_key_deriver.get_metrics_snapshot()
print("Current metrics:", metrics)

Operational Considerations
	•	Lockout and Rate Limiting: Identities are locked out after 10 failed attempts for 5 minutes to prevent brute-force attacks.
	•	Entropy Sources: Uses runtime entropy snapshots; fallback to deterministic entropy string possible.
	•	Logging: Logs key events, errors, and warnings with detailed context.
	•	Thread Safety: Internal counters and state use locks for concurrency safety.
	•	Security: Salt and key stretching increase difficulty of key recovery from outputs.
	•	Deterministic Mode: Disable salt and fix entropy to reproduce keys consistently.

⸻

Integration Guide
	•	Import the singleton symbolic_key_deriver to use throughout your application.
	•	Use the identity parameter to track users or sessions and enforce lockouts.
	•	Integrate with your monitoring stack by polling get_metrics_snapshot().
	•	Tune MAX_ATTEMPTS and lockout_time constants if needed for your threat model.
	•	Extend the entropy source for higher security by customizing _get_entropy.

⸻

If you want, I can also provide this as a markdown file or as extended docstrings in the Python module.

⸻


