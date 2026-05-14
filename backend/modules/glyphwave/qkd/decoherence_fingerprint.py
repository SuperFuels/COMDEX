import hashlib
import json
from typing import Dict, Optional

class DecoherenceFingerprint:
    """
    Computes and verifies decoherence fingerprints (collapse hashes) for tamper detection.
    """

    @staticmethod
    def compute_fingerprint(trace: Dict, entropy: float, wave_id: str) -> str:
        """
        Generate a collapse fingerprint based on symbolic trace, entropy, and wave ID.
        """
        payload = {
            "wave_id": wave_id,
            "entropy": round(entropy, 6),
            "trace_hash": DecoherenceFingerprint._hash_trace(trace)
        }
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        return fingerprint

    @staticmethod
    def verify_fingerprint(expected: str, trace: Dict, entropy: float, wave_id: str) -> bool:
        """
        Recompute and compare fingerprint against expected.
        """
        actual = DecoherenceFingerprint.compute_fingerprint(trace, entropy, wave_id)
        return actual == expected

    @staticmethod
    def _hash_trace(trace: Dict) -> str:
        """
        Reduce symbolic trace into stable hash for fingerprinting.
        """
        try:
            compressed = json.dumps(trace, sort_keys=True, separators=(",", ":"))
            return hashlib.md5(compressed.encode()).hexdigest()
        except Exception as e:
            return "invalid_trace_hash"


# Example Usage
if __name__ == "__main__":
    trace_example = {"path": ["a", "b", "c"], "node_count": 3}
    entropy_val = 0.872321
    wave_id_val = "wave_abc_123"

    fp = DecoherenceFingerprint.compute_fingerprint(trace_example, entropy_val, wave_id_val)
    print("Generated Fingerprint:", fp)

    assert DecoherenceFingerprint.verify_fingerprint(fp, trace_example, entropy_val, wave_id_val)