# File: backend/modules/glyphwave/gkey_model.py

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict
from uuid import uuid4
from datetime import datetime, timedelta
import time
import hashlib
import json

# External dependency
from backend.modules.glyphwave.qkd.decoherence_fingerprint import DecoherenceFingerprint


def generate_hash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def current_timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"


@dataclass
class GKey:
    """
    GKey = GlyphWave EntangledKey used for Quantum Key Distribution and symbolic cryptographic collapse tracking.
    Includes tamper detection, decoherence fingerprinting, and lifecycle management.
    """

    # Core Identifiers
    key_id: str = field(default_factory=lambda: str(uuid4()))
    wave_id: Optional[str] = None

    # Cryptographic Material
    public_part: Dict = field(default_factory=dict)
    private_part: Dict = field(default_factory=dict)  # Should remain sender-only
    collapse_token: Optional[str] = None  # Optional advanced collapse check

    # Security Properties
    entropy: float = 1.0  # Ideal = 1.0 (full entropy)
    coherence_level: float = 1.0  # 0.0–1.0, may degrade
    decoherence_fingerprint: Optional[str] = None  # Calculated from wave state
    collapse_hash: Optional[str] = None  # Tamper detection

    # Origin Trace
    origin_trace: Optional[Dict] = field(default_factory=dict)
    entropy_seed: Optional[str] = None  # Hash of initial entropy material
    renegotiated_from: Optional[str] = None

    # Lifecycle
    issued_at: str = field(default_factory=current_timestamp)
    created_at: float = field(default_factory=lambda: time.time())  # epoch
    expires_at: Optional[str] = None

    # State Flags
    verified: bool = False
    compromised: bool = False

    def is_valid(self) -> bool:
        if self.compromised:
            return False
        if self.expires_at:
            try:
                expiry = datetime.fromisoformat(self.expires_at.replace("Z", ""))
                return datetime.utcnow() < expiry
            except Exception:
                return False
        return True

    def to_dict(self, include_private: bool = False) -> Dict:
        """
        Convert GKey to dictionary.
        If include_private=False, omits private key material.
        """
        base = asdict(self)
        if not include_private:
            base.pop("private_part", None)
        return base

    def to_json(self, include_private: bool = False) -> str:
        return json.dumps(self.to_dict(include_private), indent=2)

    @staticmethod
    def from_dict(data: Dict) -> 'GKey':
        return GKey(
            key_id=data.get("key_id"),
            wave_id=data.get("wave_id"),
            public_part=data.get("public_part", {}),
            private_part=data.get("private_part", {}),
            collapse_token=data.get("collapse_token"),
            entropy=data.get("entropy", 1.0),
            coherence_level=data.get("coherence_level", 1.0),
            decoherence_fingerprint=data.get("decoherence_fingerprint"),
            collapse_hash=data.get("collapse_hash"),
            origin_trace=data.get("origin_trace", {}),
            entropy_seed=data.get("entropy_seed"),
            renegotiated_from=data.get("renegotiated_from"),
            issued_at=data.get("issued_at", current_timestamp()),
            created_at=data.get("created_at", time.time()),
            expires_at=data.get("expires_at"),
            verified=data.get("verified", False),
            compromised=data.get("compromised", False),
        )

    def bind_to_wave(self, wave_state):
        """
        Binds this GKey to a given wave state.
        Captures trace ID, entropy hash, coherence level, and generates fingerprint.
        """
        self.wave_id = wave_state.id
        self.origin_trace = wave_state.trace_id
        self.entropy_seed = wave_state.entropy_hash
        self.coherence_level = wave_state.coherence
        self.decoherence_fingerprint = DecoherenceFingerprint.compute_fingerprint(
            trace=wave_state.trace,
            entropy=wave_state.entropy,
            wave_id=wave_state.id
        )

    def generate_collapse_hash(self, context_data: str) -> str:
        """
        Generate a collapse hash for tamper detection.
        Hashes together key + wave context + entropy + coherence.
        """
        full_data = f"{self.key_id}:{self.wave_id}:{context_data}:{self.entropy}:{self.coherence_level}"
        self.collapse_hash = generate_hash(full_data)
        return self.collapse_hash

    def mark_compromised(self, reason: Optional[str] = None):
        """
        Marks this GKey as compromised — sets entropy/coherence to 0.
        Logs the reason in origin_trace.
        """
        self.compromised = True
        self.coherence_level = 0.0
        self.entropy = 0.0
        if reason:
            self.origin_trace["compromise_reason"] = reason

    def rekey(self, new_wave_id: Optional[str] = None) -> 'GKey':
        """
        Generate a new GKey using the same key material, but new key ID and optionally new wave_id.
        """
        return GKey(
            wave_id=new_wave_id or self.wave_id,
            public_part=self.public_part,
            private_part=self.private_part,
            entropy=1.0,
            coherence_level=1.0,
            origin_trace={"rekeyed_from": self.key_id},
            renegotiated_from=self.key_id
        )