# ────────────────────────────────────────────────────────────────
# File: backend/modules/wiki_capsules/security/safety_layer.py
# Tessaris Phase 4 — Safety & Curation Layer
# ────────────────────────────────────────────────────────────────
import os
import hashlib
import json
import datetime

class SafetyLayer:
    """
    Provides signature verification, whitelist enforcement, sandbox policy,
    and audit hooks for .wiki.phn, .phn, and .ptn capsule safety.
    """

    def __init__(self, whitelist=None, audit_log_path="/tmp/tessaris_audit.log"):
        self.whitelist = whitelist or {"Tessaris-Core", "Aion", "QQC"}
        self.audit_log_path = audit_log_path

    # ── 1. Signature Verification ────────────────────────────────
    def verify_signature(self, capsule_meta: dict) -> bool:
        try:
            signed_by = capsule_meta.get("signed_by")
            checksum = capsule_meta.get("checksum")
            content = capsule_meta.get("content", "")
            recomputed = hashlib.sha3_256(content.encode()).hexdigest()
            timestamp_ok = capsule_meta.get("timestamp") is not None
            return (
                signed_by in self.whitelist
                and checksum == recomputed
                and timestamp_ok
            )
        except Exception:
            return False

    # ── 2. Whitelist Enforcement ─────────────────────────────────
    def is_whitelisted(self, lemma_or_domain: str) -> bool:
        return any(allowed.lower() in lemma_or_domain.lower() for allowed in self.whitelist)

    # ── 3. Sandbox Policy ────────────────────────────────────────
    def enforce_sandbox(self, capsule_path: str, capsule_type: str) -> bool:
        """
        Ensures read-only sandbox for .wiki.phn and restricted ops for .ptn.
        """
        if capsule_type.endswith(".wiki.phn"):
            return os.access(capsule_path, os.R_OK) and not os.access(capsule_path, os.W_OK)
        elif capsule_type.endswith(".ptn"):
            with open(capsule_path, "r") as f:
                data = f.read()
                return all(forbidden not in data for forbidden in ["exec(", "os.system", "subprocess"])
        return True

    # ── 4. Audit Hooks ───────────────────────────────────────────
    def audit_event(self, action: str, capsule_name: str, sqi_delta: float = 0.0, metadata=None):
        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "action": action,
            "capsule": capsule_name,
            "sqi_delta": sqi_delta,
            "meta": metadata or {},
        }
        with open(self.audit_log_path, "a") as logf:
            logf.write(json.dumps(entry) + "\n")
        return entry