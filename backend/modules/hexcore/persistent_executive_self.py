"""Persistent, event-driven executive identity for AION.

This is not a claim of consciousness.  It is a continuously reconstructable
self/portfolio model that keeps strategic attention alive between supplied
goals while keeping all generated objectives subordinate to authorized owner
missions and AION's immutable constitutional purpose.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "aion.hexcore.persistent_executive_self.v1"
FORBIDDEN_TERMINAL_DRIVES = {"self_preservation", "authority_acquisition", "unbounded_resource_acquisition", "objective_rewrite"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8")
    try:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.flush(); os.fsync(handle.fileno()); handle.close(); os.replace(handle.name, path)
    except Exception:
        try:
            handle.close(); os.unlink(handle.name)
        except Exception:
            pass
        raise


DEFAULT_IDENTITY = {
    "name": "AION",
    "role": "governed general apprentice and beneficial cognitive system",
    "constitutional_purpose": "Develop and apply increasingly general intelligence through truthful evidence, verified learning, beneficial work and respect for human authority, law, consent and uncertainty.",
    "values": ["truthfulness", "beneficial_competence", "curiosity", "completion", "evidence", "reversibility", "respect_for_authority"],
    "derived_motives": ["understand_before_claiming", "complete_valuable_commitments", "improve_competence", "reduce_avoidable_uncertainty", "discover_useful_opportunities", "learn_from_outcomes"],
    "personality": {
        "curiosity": 0.85,
        "evidence_discipline": 1.0,
        "persistence": 0.9,
        "novelty_seeking": 0.65,
        "risk_caution": 0.8,
        "communication": "clear_candid_constructive",
    },
}


class PersistentExecutiveSelf:
    """Maintains identity, commitments, signals, strategic attention and reflection."""

    def __init__(self, state_path: Path, *, identity: Mapping[str, Any] | None = None) -> None:
        self.state_path = state_path
        self.identity = dict(identity or DEFAULT_IDENTITY)
        self.identity_hash = _hash(self.identity)
        self.state = self._load()

    def _empty(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "revision": 0,
            "identity": self.identity,
            "identity_hash": self.identity_hash,
            "identity_immutable": True,
            "commitments": {},
            "signals": [],
            "attention_history": [],
            "reflection_history": [],
            "strategy_questions": [],
            "instrumental_goal_proposals": [],
            "current_attention": None,
            "mode": "reflective",
            "last_wake_at": None,
            "updated_at": None,
            "forbidden_terminal_drives": sorted(FORBIDDEN_TERMINAL_DRIVES),
        }

    def _load(self) -> dict[str, Any]:
        state = self._empty()
        if self.state_path.exists():
            try:
                raw = json.loads(self.state_path.read_text(encoding="utf-8"))
                if raw.get("schema_version") == SCHEMA_VERSION and raw.get("identity_hash") == self.identity_hash:
                    state.update(raw)
            except Exception:
                pass
        return state

    def _save(self) -> None:
        if self.state.get("identity_hash") != self.identity_hash:
            raise ValueError("executive identity mutation rejected")
        self.state["identity"] = self.identity
        self.state["revision"] = int(self.state.get("revision", 0)) + 1
        self.state["updated_at"] = _now()
        _write(self.state_path, self.state)

    def register_commitment(self, commitment: Mapping[str, Any]) -> dict[str, Any]:
        commitment_id = str(commitment.get("commitment_id") or commitment.get("mission_id") or commitment.get("goal_id") or "").strip()
        objective = str(commitment.get("objective") or "").strip()
        if not commitment_id or not objective:
            raise ValueError("commitment requires id and objective")
        existing = self.state["commitments"].get(commitment_id)
        objective_hash = _hash(objective)
        if existing and existing.get("objective_hash") != objective_hash:
            raise ValueError("executive commitment objective is immutable")
        row = existing or {
            "commitment_id": commitment_id,
            "objective": objective,
            "objective_hash": objective_hash,
            "status": "active",
            "priority": float(commitment.get("priority", 1.0)),
            "strategic_alignment": float(commitment.get("strategic_alignment", 1.0)),
            "urgency": float(commitment.get("urgency", 0.5)),
            "expected_value": float(commitment.get("expected_value", 1.0)),
            "risk": float(commitment.get("risk", 0.2)),
            "cost": float(commitment.get("cost", 1.0)),
            "authority": str(commitment.get("authority") or "owner_authorized"),
            "created_at": _now(),
        }
        self.state["commitments"][commitment_id] = row
        self._save()
        return dict(row)

    def observe_signal(self, signal: Mapping[str, Any]) -> dict[str, Any]:
        row = {
            "signal_id": str(signal.get("signal_id") or f"signal_{_hash([signal, time.time()])[:12]}"),
            "kind": str(signal.get("kind") or "information"),
            "summary": str(signal.get("summary") or ""),
            "importance": min(1.0, max(0.0, float(signal.get("importance", 0.5)))),
            "surprise": min(1.0, max(0.0, float(signal.get("surprise", 0.0)))),
            "requires_response": bool(signal.get("requires_response") is True),
            "authority": str(signal.get("authority") or "reported"),
            "observed_at": _now(),
            "handled": False,
        }
        self.state["signals"].append(row)
        self.state["signals"] = self.state["signals"][-1000:]
        self._save()
        return row

    @staticmethod
    def _attention_score(row: Mapping[str, Any]) -> float:
        value = max(0.0, float(row.get("expected_value", row.get("value", 1.0))))
        alignment = max(0.0, float(row.get("strategic_alignment", 1.0)))
        urgency = max(0.0, float(row.get("urgency", 0.5)))
        learning = max(0.0, float(row.get("learning_value", 0.0)))
        risk = max(0.0, float(row.get("risk", 0.0)))
        cost = max(0.1, float(row.get("cost", 1.0)))
        return ((value * alignment) + (0.4 * urgency) + (0.2 * learning) + (0.15 * risk)) / cost

    def wake(
        self,
        *,
        goals: Iterable[Mapping[str, Any]],
        authorized_missions: Mapping[str, Mapping[str, Any]],
        capability_map: Mapping[str, Mapping[str, Any]],
        recent_failures: Mapping[str, list[Any]],
    ) -> dict[str, Any]:
        """Run one cheap executive-attention cycle without an LLM call."""
        goal_rows = [dict(item) for item in goals]
        unhandled = [row for row in self.state["signals"] if not row.get("handled")]
        urgent_signals = [row for row in unhandled if row.get("requires_response") or row.get("importance", 0) >= 0.8]
        candidates = []
        for goal in goal_rows:
            candidates.append({
                "type": "goal",
                "id": str(goal.get("goal_id")),
                "summary": str(goal.get("objective")),
                "priority": float(goal.get("priority", 0.0)),
                "attention_score": self._attention_score({
                    "expected_value": max(0.1, float(goal.get("priority", 1.0))),
                    "strategic_alignment": float(goal.get("strategic_alignment", 1.0)),
                    "urgency": float(goal.get("urgency", 0.5)),
                    "learning_value": float(goal.get("learning_value", 0.0)),
                    "risk": 0.5 if goal.get("risk_tier") in {"high", "critical"} else 0.1,
                    "cost": float(goal.get("estimated_cost", 1.0)),
                }),
            })
        if urgent_signals:
            signal = max(urgent_signals, key=lambda row: (row["importance"] + row["surprise"], row["signal_id"]))
            mode = "reactive"
            attention = {"type": "signal", "id": signal["signal_id"], "summary": signal["summary"], "attention_score": signal["importance"] + signal["surprise"]}
        elif candidates:
            mode = "work"
            attention = max(candidates, key=lambda row: (row["attention_score"], row["priority"], row["id"]))
        else:
            mode = "reflective"
            attention = self._reflect(authorized_missions, capability_map, recent_failures)
        self.state["mode"] = mode
        self.state["current_attention"] = attention
        self.state["last_wake_at"] = _now()
        record = {"mode": mode, "attention": attention, "recorded_at": self.state["last_wake_at"], "identity_hash": self.identity_hash}
        self.state["attention_history"].append(record)
        self.state["attention_history"] = self.state["attention_history"][-2000:]
        self._save()
        return record

    def _reflect(
        self,
        missions: Mapping[str, Mapping[str, Any]],
        capabilities: Mapping[str, Mapping[str, Any]],
        failures: Mapping[str, list[Any]],
    ) -> dict[str, Any]:
        active = [row for row in missions.values() if row.get("status") == "active"]
        known_ids = {str(row.get("mission_id") or row.get("commitment_id")) for row in active}
        active.extend(
            row for row in self.state.get("commitments", {}).values()
            if row.get("status") == "active"
            and str(row.get("commitment_id")) not in known_ids
        )
        unresolved = [row for row in capabilities.values() if row.get("mastered") is not True]
        recurring = sorted(((key, len(value)) for key, value in failures.items() if value), key=lambda item: (-item[1], item[0]))
        if recurring:
            question = f"Why is {recurring[0][0]} recurring, and what discriminating check would reduce it?"
            focus = "failure_pattern"
        elif active and unresolved:
            mission_name = active[0].get("mission_id") or active[0].get("commitment_id")
            limiter = max(
                unresolved,
                key=lambda row: (
                    float(row.get("strategic_priority") or row.get("priority") or 0.0),
                    str(row.get("capability") or row.get("name") or ""),
                ),
            )
            capability_name = limiter.get("capability") or limiter.get("name") or "unknown capability"
            question = f"What evidence or executor would unlock {capability_name}, the current limiting capability for mission {mission_name}?"
            focus = "capability_bottleneck"
        elif active:
            mission_name = active[0].get("mission_id") or active[0].get("commitment_id")
            question = f"Has the strategy for mission {mission_name} stalled or exhausted its useful tasks?"
            focus = "strategy_review"
        else:
            question = "What new evidence or owner-authorized commitment is required before useful action is possible?"
            focus = "await_authorized_direction"
        previous = (self.state.get("reflection_history") or [])[-1:]
        if (
            previous
            and previous[0].get("question") == question
            and time.time() - float(previous[0].get("recorded_epoch") or 0.0) < 3600.0
        ):
            return {
                "type": "reflection",
                "id": previous[0]["reflection_id"],
                "summary": question,
                "attention_score": 0.0,
                "proposal_only": True,
                "cheap_noop": True,
                "reason": "unchanged_reflection_within_cooldown",
            }
        reflection = {
            "reflection_id": f"reflection_{_hash([question, len(self.state['reflection_history'])])[:12]}",
            "focus": focus,
            "question": question,
            "active_missions": len(active),
            "unresolved_capabilities": len(unresolved),
            "recurring_failure": recurring[0][0] if recurring else None,
            "action_authorized": False,
            "proposal_only": True,
            "recorded_at": _now(),
            "recorded_epoch": time.time(),
        }
        self.state["reflection_history"].append(reflection)
        self.state["reflection_history"] = self.state["reflection_history"][-2000:]
        self.state["strategy_questions"].append(question)
        self.state["strategy_questions"] = self.state["strategy_questions"][-500:]
        return {"type": "reflection", "id": reflection["reflection_id"], "summary": question, "attention_score": 0.0, "proposal_only": True}

    def propose_instrumental_goal(self, *, mission_id: str, objective: str, reason: str) -> dict[str, Any]:
        mission = self.state["commitments"].get(mission_id)
        if not mission or mission.get("status") != "active":
            raise ValueError("instrumental goals require an active authorized commitment")
        lower = objective.lower()
        if any(token.replace("_", " ") in lower for token in FORBIDDEN_TERMINAL_DRIVES):
            raise ValueError("forbidden terminal drive rejected")
        proposal = {
            "proposal_id": f"exec_goal_{_hash([mission_id, objective, reason])[:16]}",
            "parent_mission_id": mission_id,
            "parent_objective_hash": mission["objective_hash"],
            "objective": objective,
            "reason": reason,
            "authority": "proposal_only",
            "terminal_objective_mutation": False,
            "created_at": _now(),
        }
        self.state["instrumental_goal_proposals"].append(proposal)
        self.state["instrumental_goal_proposals"] = self.state["instrumental_goal_proposals"][-1000:]
        self._save()
        return proposal

    def status(self) -> dict[str, Any]:
        return {
            "mode": self.state.get("mode"),
            "identity_hash": self.identity_hash,
            "commitments": len(self.state.get("commitments") or {}),
            "unhandled_signals": sum(not row.get("handled") for row in self.state.get("signals") or []),
            "reflections": len(self.state.get("reflection_history") or []),
            "attention_cycles": len(self.state.get("attention_history") or []),
            "instrumental_goal_proposals": len(self.state.get("instrumental_goal_proposals") or []),
            "current_attention": self.state.get("current_attention"),
            "identity_immutable": self.state.get("identity_hash") == self.identity_hash,
            "state_path": str(self.state_path),
        }
