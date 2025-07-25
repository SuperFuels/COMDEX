Symbolic Key Derivation Module

Overview

The Symbolic Key Derivation module securely derives cryptographic keys based on symbolic inputs combined with runtime entropy and security parameters. It supports:
	•	Combining trust level, emotion level, timestamp, and optional seed phrase into entropy.
	•	Symbolic evaluation of entropy seed via a codex adapter.
	•	Key stretching for cryptographic hardness.
	•	Brute-force attempt tracking with lockouts and rate-limiting.
	•	Deterministic mode for testing (disabling salts and entropy).
	•	Thread-safe state management.

This module is intended for ephemeral cryptographic key generation in AI workflows where symbolic context and dynamic runtime entropy contribute to security.

⸻

Features
	•	Deterministic and non-deterministic key derivation: Supports disabling salt and entropy for reproducible keys during testing.
	•	Lockout and brute-force protection: Automatically tracks failed attempts per identity and applies temporary lockouts.
	•	Pluggable symbolic adapter: Integrates with a codex adapter for symbolic computation; falls back to SHA-256 hashing.
	•	Thread-safe internal state: Uses locking to protect attempt counters and lockout status.
	•	Logging: Logs warnings and errors for suspicious activity and failures.

⸻

Class: SymbolicKeyDerivation

Initialization

skd = SymbolicKeyDerivation()

Methods

derive_key

Derives a secure cryptographic key.

derive_key(
    trust_level: float,
    emotion_level: float,
    timestamp: float,
    identity: Optional[str] = None,
    seed_phrase: Optional[str] = None,
    use_salt: bool = True,
    fixed_entropy: Optional[str] = None
) -> Optional[bytes]

	•	Parameters:
	•	trust_level: Numeric trust level influencing key entropy.
	•	emotion_level: Numeric emotion level influencing key entropy.
	•	timestamp: Numeric timestamp (epoch seconds).
	•	identity: Optional string used for tracking lockouts and rate limits.
	•	seed_phrase: Optional string seed phrase to alter output.
	•	use_salt: Whether to add salt and nonce for non-deterministic keys.
	•	fixed_entropy: Optional fixed entropy string to override runtime entropy (for testing).
	•	Returns: Derived key bytes, or None if locked out or on error.

verify_key

Verifies a provided key matches expected derivation.

verify_key(
    key: bytes,
    trust_level: float,
    emotion_level: float,
    timestamp: float,
    identity: Optional[str] = None,
    seed_phrase: Optional[str] = None
) -> bool

	•	Returns: True if key matches derived key, False otherwise.

⸻

Internal Details
	•	Uses runtime entropy snapshot from memory_engine.get_runtime_entropy_snapshot().
	•	Symbolic evaluation through a codex adapter or fallback SHA-256.
	•	Key stretching with 10,000 iterations of SHA-256 for hardness.
	•	Lockouts last 300 seconds after 10 failed attempts per identity.
	•	Thread-safe with internal locking on shared state.

⸻

Usage Example

from backend.modules.glyphnet.symbolic_key_derivation import symbolic_key_deriver

# Derive a key for a session with seed phrase and salt
key = symbolic_key_deriver.derive_key(
    trust_level=0.75,
    emotion_level=0.25,
    timestamp=time.time(),
    identity="session123",
    seed_phrase="my_secret_seed",
    use_salt=True
)

# Verify the key later
is_valid = symbolic_key_deriver.verify_key(
    key,
    trust_level=0.75,
    emotion_level=0.25,
    timestamp=time.time(),
    identity="session123",
    seed_phrase="my_secret_seed"
)

Operational Notes
	•	Ensure identity is consistent per user/session for lockout enforcement.
	•	Disable salt and runtime entropy (use_salt=False, fixed_entropy="") for reproducible testing.
	•	Monitor logs for warnings about repeated failed attempts or lockouts.
	•	Integration with a real symbolic codex adapter is required for production; fallback uses SHA-256.

⸻

TODO / Future Enhancements
	•	Centralized runtime metrics: counts of derivations, failures, lockouts.
	•	Alerting and automated mitigation on suspicious patterns.
	•	API docs and onboarding guides.
	•	Integration examples with cryptographic modules and ephemeral key lifecycles.

    