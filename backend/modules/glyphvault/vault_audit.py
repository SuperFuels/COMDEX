# backend/modules/glyphvault/vault_audit.py

import time
from threading import Lock
from collections import deque
from typing import Dict, Any, List

from backend.modules.glyphvault.vault_logger import log_event

class VaultAudit:
    """
    Tracks vault audit logs and access metrics in memory with optional persistence.
    """

    MAX_LOG_ENTRIES = 1000

    def __init__(self):
        self._lock = Lock()
        self._logs = deque(maxlen=self.MAX_LOG_ENTRIES)
        self._metrics = {
            "total_saves": 0,
            "total_restores": 0,
            "total_deletes": 0,
            "access_denied": 0,
        }

    def record_event(self, event_type: str, container_id: str, user_id: str = "unknown", extra: Dict[str, Any] = None):
        """
        Record an audit event with timestamp and increment metrics.

        Args:
            event_type (str): One of "SAVE", "RESTORE", "DELETE", "ACCESS_DENIED", etc.
            container_id (str): Container or snapshot identifier
            user_id (str): Optional user or avatar id triggering the event
            extra (Dict[str, Any]): Optional additional data
        """
        timestamp = time.time()
        log_entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "container_id": container_id,
            "user_id": user_id,
            "extra": extra or {},
        }
        with self._lock:
            self._logs.append(log_entry)
            if event_type == "SAVE":
                self._metrics["total_saves"] += 1
            elif event_type == "RESTORE":
                self._metrics["total_restores"] += 1
            elif event_type == "DELETE":
                self._metrics["total_deletes"] += 1
            elif event_type == "ACCESS_DENIED":
                self._metrics["access_denied"] += 1

        # Also log to centralized vault logger
        log_event(event_type, log_entry)

    def get_recent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent audit logs, newest first.

        Args:
            limit (int): Number of log entries to return

        Returns:
            List[Dict[str, Any]]: Recent audit log entries
        """
        with self._lock:
            return list(reversed(list(self._logs)[-limit:]))

    def get_metrics(self) -> Dict[str, int]:
        """
        Get current aggregate metrics.

        Returns:
            Dict[str, int]: Metrics summary
        """
        with self._lock:
            return self._metrics.copy()

# Singleton instance
VAULT_AUDIT = VaultAudit()