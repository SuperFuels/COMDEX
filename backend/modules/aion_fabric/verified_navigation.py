from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, Iterable
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class UniversalVerifiedNavigation:
    """Persistent observe-act-observe-verify transactions for restricted displays."""

    _lock = threading.RLock()
    MAX_ATTEMPTS = 3

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "verified_navigation"
        self.path = self.root / "state.json"
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _initial() -> Dict[str, Any]:
        return {
            "schema_version": "pilot.verified-navigation.store.v1",
            "active": None,
            "last_transaction": None,
            "route_memory": {},
            "history": [],
            "updated_at": utc_now_iso(),
        }

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return self._initial()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else self._initial()
        except (OSError, json.JSONDecodeError):
            return self._initial()

    def _write(self, state: Dict[str, Any]) -> None:
        state["updated_at"] = utc_now_iso()
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)

    @staticmethod
    def _memory_key(device_id: str, surface: str, goal: str, route_id: str) -> str:
        return canonical_hash({"device": device_id, "surface": surface, "goal": goal, "route": route_id})

    @staticmethod
    def _safe_routes(routes: Iterable[Dict[str, Any]]) -> list[Dict[str, Any]]:
        safe = []
        for route in list(routes)[:5]:
            if not isinstance(route, dict):
                continue
            route_id = str(route.get("route_id") or "")[:80]
            command = str(route.get("command") or "")[:80]
            if route_id and command:
                safe.append({"route_id": route_id, "command": command, "arguments": dict(route.get("arguments") or {})})
        if not safe:
            raise ValueError("At least one bounded navigation route is required")
        return safe

    def start(
        self,
        *,
        device_id: str,
        surface: str,
        goal: str,
        expected: Dict[str, Any],
        routes: Iterable[Dict[str, Any]],
        before: Dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Dict[str, Any]:
        if expected.get("kind") not in {"surface", "view", "view_not", "screen_changed", "surface_screen_changed", "text_contains", "device_field", "receipt_verified"}:
            raise ValueError("Unsupported navigation verification criterion")
        idempotency_key = re.sub(r"[^A-Za-z0-9_.:-]+", "", str(idempotency_key or ""))[:120]
        route_list = self._safe_routes(routes)
        with self._lock:
            state = self._read()
            if idempotency_key:
                candidates = [state.get("active"), state.get("last_transaction"), *reversed(list(state.get("history") or [])[-20:])]
                duplicate = next((dict(item) for item in candidates if isinstance(item, dict) and item.get("idempotency_key") == idempotency_key), None)
                if duplicate:
                    duplicate["duplicate_suppressed"] = True
                    return duplicate
            previous = state.get("active")
            if isinstance(previous, dict):
                previous = dict(previous)
                previous["status"] = "superseded_not_verified"
                previous["completed_at"] = utc_now_iso()
                previous["transaction_hash"] = canonical_hash({k: v for k, v in previous.items() if k != "transaction_hash"})
                history = list(state.get("history") or [])
                history.append(previous)
                state["history"] = history[-250:]
                state["last_transaction"] = previous
            memory = dict(state.get("route_memory") or {})
            route_list.sort(
                key=lambda route: (
                    -int(dict(memory.get(self._memory_key(device_id, surface, goal, route["route_id"])) or {}).get("successes") or 0),
                    int(dict(memory.get(self._memory_key(device_id, surface, goal, route["route_id"])) or {}).get("failures") or 0),
                )
            )
            transaction = {
                "schema_version": "pilot.verified-navigation.transaction.v1",
                "transaction_id": f"navtx_{uuid4().hex}",
                "device_id": device_id[:160],
                "surface": surface[:80],
                "goal": goal[:160],
                "expected": dict(expected),
                "routes": route_list,
                "route_index": 0,
                "attempts": [],
                "status": "ready_to_act",
                "before": dict(before or {}),
                "created_at": utc_now_iso(),
                "idempotency_key": idempotency_key,
            }
            transaction["transaction_hash"] = canonical_hash(transaction)
            state["active"] = transaction
            self._write(state)
            return dict(transaction)

    def current_route(self) -> Dict[str, Any]:
        active = dict(self._read().get("active") or {})
        if not active:
            raise ValueError("No verified navigation transaction is active")
        routes = list(active.get("routes") or [])
        index = int(active.get("route_index") or 0)
        if index >= len(routes):
            raise ValueError("No navigation route remains")
        return dict(routes[index])

    @staticmethod
    def _device_field_matches(expected: Dict[str, Any], after: Dict[str, Any]) -> bool:
        field = str(expected.get("field") or "")
        if not field:
            return False
        value: Any = after
        for part in field.split("."):
            if not isinstance(value, dict) or part not in value:
                return False
            value = value[part]
        if "equals" in expected:
            return value == expected["equals"]
        if expected.get("present"):
            return value not in {None, ""}
        return False

    def record_action_receipt(self, receipt: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            state = self._read()
            active = state.get("active")
            if not isinstance(active, dict):
                raise ValueError("No verified navigation transaction is active")
            if len(active.get("attempts") or []) >= self.MAX_ATTEMPTS:
                raise RuntimeError("The bounded navigation attempt limit is exhausted")
            route = self.current_route()
            attempt = {
                "attempt": len(active.get("attempts") or []) + 1,
                "route_id": route["route_id"],
                "receipt_id": str(receipt.get("receipt_id") or ""),
                "transport_verified": bool(receipt.get("verified")),
                "action": str(receipt.get("action") or route["command"]),
                "after_device": dict(receipt.get("after") or {}),
                "status": "transport_delivered",
                "acted_at": utc_now_iso(),
            }
            active.setdefault("attempts", []).append(attempt)
            expected = dict(active.get("expected") or {})
            if expected.get("kind") == "receipt_verified":
                return self._finish_locked(state, success=attempt["transport_verified"], evidence={"kind": "read_after_write_receipt", "after": attempt["after_device"]})
            if expected.get("kind") == "device_field" and attempt["transport_verified"]:
                success = self._device_field_matches(expected, attempt["after_device"])
                return self._finish_locked(state, success=success, evidence={"kind": "device_receipt", "after": attempt["after_device"]})
            if not attempt["transport_verified"]:
                return self._finish_locked(state, success=False, evidence={"kind": "transport_failure", "after": attempt["after_device"]})
            active["status"] = "awaiting_after_observation"
            active["transaction_hash"] = canonical_hash({k: v for k, v in active.items() if k != "transaction_hash"})
            self._write(state)
            return dict(active)

    def record_observation(self, observation: Dict[str, Any]) -> Dict[str, Any] | None:
        with self._lock:
            state = self._read()
            active = state.get("active")
            if not isinstance(active, dict) or active.get("status") != "awaiting_after_observation":
                return None
            expected = dict(active.get("expected") or {})
            inference = dict(observation.get("inference") or observation.get("screen_understanding") or {})
            kind = expected.get("kind")
            if kind == "surface":
                success = str(inference.get("surface") or "") == str(expected.get("value") or "")
            elif kind == "view":
                success = str(inference.get("view") or "") == str(expected.get("value") or "")
            elif kind == "view_not":
                success = str(inference.get("view") or "") != str(expected.get("value") or "")
            elif kind == "screen_changed":
                before_hash = str((active.get("before") or {}).get("image_sha256") or "")
                after_hash = str(observation.get("image_sha256") or "")
                success = bool(before_hash and after_hash and before_hash != after_hash)
            elif kind == "surface_screen_changed":
                before_hash = str((active.get("before") or {}).get("image_sha256") or "")
                after_hash = str(observation.get("image_sha256") or "")
                success = (
                    bool(before_hash and after_hash and before_hash != after_hash)
                    and str(inference.get("surface") or "") == str(expected.get("surface") or "")
                )
            elif kind == "text_contains":
                expected_text = " ".join(str(expected.get("value") or "").lower().split())
                observed_text = " ".join(
                    str(value).lower()
                    for value in list(observation.get("texts") or [])[:100]
                    if isinstance(value, str)
                )
                success = bool(expected_text and expected_text in " ".join(observed_text.split()))
            else:
                success = self._device_field_matches(expected, dict(observation.get("device_state") or {}))
            evidence = {
                "kind": "structured_observation",
                "observation_id": str((observation.get("screen_understanding") or {}).get("observation_id") or ""),
                "image_sha256": str(observation.get("image_sha256") or ""),
                "surface": str(inference.get("surface") or ""),
                "view": str(inference.get("view") or ""),
                "criterion": expected,
            }
            return self._finish_locked(state, success=success, evidence=evidence)

    def record_owner_confirmation(self, *, transaction_id: str, confirmed: bool) -> Dict[str, Any]:
        """Close an OCR-ambiguous result using bounded owner attestation.

        Pilot still requires both a verified transport receipt and a changed
        observer image. The owner confirmation supplies only the semantic fact
        that the requested on-screen result is visible.
        """
        with self._lock:
            state = self._read()
            active = state.get("active")
            if not isinstance(active, dict) or active.get("transaction_id") != transaction_id:
                raise ValueError("The navigation transaction is no longer active")
            if active.get("status") not in {"awaiting_after_observation", "recovery_ready"}:
                raise ValueError("The navigation transaction is not awaiting confirmation")
            attempts = list(active.get("attempts") or [])
            if not attempts or not bool(attempts[-1].get("transport_verified")):
                raise ValueError("Owner confirmation requires a verified transport receipt")
            observed = dict(active.get("failure_evidence") or active.get("after_evidence") or {})
            before_hash = str((active.get("before") or {}).get("image_sha256") or "")
            after_hash = str(observed.get("image_sha256") or "")
            if not before_hash or not after_hash or before_hash == after_hash:
                raise ValueError("Owner confirmation requires a changed observer image")
            attempted_route = str(attempts[-1].get("route_id") or "")
            for index, route in enumerate(active.get("routes") or []):
                if str(route.get("route_id") or "") == attempted_route:
                    active["route_index"] = index
                    break
            state["active"] = active
            evidence = {
                "kind": "owner_visual_confirmation",
                "confirmed": bool(confirmed),
                "image_sha256": after_hash,
                "machine_observation": observed,
                "transport_receipt_id": str(attempts[-1].get("receipt_id") or ""),
                "criterion": dict(active.get("expected") or {}),
            }
            return self._finish_locked(state, success=bool(confirmed), evidence=evidence)

    def cancel_active(self, *, reason: str = "owner_cancelled") -> Dict[str, Any] | None:
        with self._lock:
            state = self._read()
            active = state.get("active")
            if not isinstance(active, dict):
                return None
            active = dict(active)
            active["status"] = "cancelled"
            active["cancelled_at"] = utc_now_iso()
            active["cancellation_reason"] = str(reason)[:100]
            active["transaction_hash"] = canonical_hash({k: v for k, v in active.items() if k != "transaction_hash"})
            history = list(state.get("history") or [])
            history.append(active)
            state["history"] = history[-250:]
            state["last_transaction"] = active
            state["active"] = None
            self._write(state)
            return active

    def _finish_locked(self, state: Dict[str, Any], *, success: bool, evidence: Dict[str, Any]) -> Dict[str, Any]:
        active = dict(state.get("active") or {})
        attempts = list(active.get("attempts") or [])
        route = dict((active.get("routes") or [])[int(active.get("route_index") or 0)])
        key = self._memory_key(active["device_id"], active["surface"], active["goal"], route["route_id"])
        memory = dict(state.get("route_memory") or {})
        entry = dict(memory.get(key) or {"successes": 0, "failures": 0})
        field = "successes" if success else "failures"
        entry[field] = int(entry.get(field) or 0) + 1
        entry.update({
            "device_id": active["device_id"], "surface": active["surface"], "goal": active["goal"],
            "route_id": route["route_id"], "last_success": success, "updated_at": utc_now_iso(),
        })
        memory[key] = entry
        state["route_memory"] = dict(list(memory.items())[-200:])
        active["after_evidence"] = evidence
        if success:
            active["status"] = "verified"
            active["completed_at"] = utc_now_iso()
            state["last_transaction"] = active
            state["active"] = None
        elif len(attempts) < self.MAX_ATTEMPTS and int(active.get("route_index") or 0) + 1 < len(active.get("routes") or []):
            active["route_index"] = int(active.get("route_index") or 0) + 1
            active["status"] = "recovery_ready"
            active["failure_evidence"] = evidence
            state["active"] = active
        else:
            active["status"] = "not_verified"
            active["completed_at"] = utc_now_iso()
            state["last_transaction"] = active
            state["active"] = None
        active["transaction_hash"] = canonical_hash({k: v for k, v in active.items() if k != "transaction_hash"})
        if active.get("status") in {"verified", "not_verified"}:
            history = list(state.get("history") or [])
            history.append(active)
            state["history"] = history[-250:]
        self._write(state)
        return dict(active)

    def reliability_report(self, *, device_id: str | None = None, minimum_sample: int = 20) -> Dict[str, Any]:
        state = self._read()
        history = [
            dict(item) for item in list(state.get("history") or [])
            if isinstance(item, dict) and (not device_id or item.get("device_id") == device_id)
        ]
        terminal = [item for item in history if item.get("status") in {"verified", "not_verified", "superseded_not_verified"}]
        verified = [item for item in terminal if item.get("status") == "verified"]
        recovered = [item for item in verified if int(item.get("route_index") or 0) > 0]
        failures = [item for item in terminal if item.get("status") != "verified"]
        rate = round(len(verified) / len(terminal), 4) if terminal else 0.0
        by_goal: Dict[str, Dict[str, int]] = {}
        for item in terminal:
            goal = str(item.get("goal") or "unknown")
            bucket = by_goal.setdefault(goal, {"attempted": 0, "verified": 0, "not_verified": 0})
            bucket["attempted"] += 1
            bucket["verified" if item.get("status") == "verified" else "not_verified"] += 1
        return {
            "schema_version": "pilot.tv-reliability-report.v1",
            "device_id": device_id,
            "sample_size": len(terminal),
            "verified": len(verified),
            "recovered": len(recovered),
            "not_verified": len(failures),
            "verified_or_recovered_rate": rate,
            "target_rate": 0.95,
            "minimum_sample": max(1, int(minimum_sample)),
            "closure_target_met": len(terminal) >= max(1, int(minimum_sample)) and rate >= 0.95,
            "by_goal": by_goal,
            "delivery_alone_counted_as_success": False,
            "generated_at": utc_now_iso(),
        }

    def snapshot(self) -> Dict[str, Any]:
        state = self._read()
        return {
            "schema_version": "pilot.verified-navigation.snapshot.v1",
            "active": state.get("active"),
            "last_transaction": state.get("last_transaction"),
            "route_memory_count": len(state.get("route_memory") or {}),
            "reliability": self.reliability_report(),
            "policy": "Delivery is not success; every route requires device-state or structured visual evidence.",
        }
