# backend/QQC/qqc_commit_manager.py
import uuid, time, json, os
from datetime import datetime

class QQCCommitManager:
    def __init__(self, ledger_path="data/ledger/qqc_commit_log.jsonl", threshold=0.9):
        self.ledger_path = ledger_path
        os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
        self.threshold = threshold
        self.last_txn = None

    def compute_sqi(self, symbolic_c, photonic_c, holographic_c):
        # Weighted total coherence
        return 0.3 * symbolic_c + 0.4 * photonic_c + 0.3 * holographic_c

    def commit_transaction(self, symbolic_state, photonic_state, holographic_state):
        C_total = self.compute_sqi(
            symbolic_state.get("coherence", 0.0),
            photonic_state.get("coherence", 0.0),
            holographic_state.get("coherence", 0.0),
        )
        txn = {
            "txn_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "symbolic_state": symbolic_state,
            "photonic_state": photonic_state,
            "holographic_state": holographic_state,
            "C_total": C_total,
            "status": "committed" if C_total >= self.threshold else "pending",
        }

        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(txn) + "\n")

        self.last_txn = txn
        return txn

    def rollback_to_last_commit(self):
        try:
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                lines = [json.loads(x) for x in f.readlines() if x.strip()]
            committed = [t for t in lines if t["status"] == "committed"]
            if not committed:
                return None
            last = committed[-1]
            return last
        except Exception as e:
            return {"status": "rollback_failed", "error": str(e)}