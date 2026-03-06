# /workspaces/COMDEX/backend/modules/aion_equities/live_variable_tracker.py
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from backend.modules.aion_equities.company_trigger_map_store import CompanyTriggerMapStore
from backend.modules.aion_equities.feed_registry import FeedRegistry


_ALLOWED_TRIGGER_STATES = {
    "inactive",
    "early_watch",
    "building",
    "confirmed",
    "broken",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _infer_trigger_state(
    *,
    current_state: str,
    threshold_rule: str,
    previous_value: Any,
    value: Any,
) -> str:
    current_state = str(current_state or "inactive").strip().lower()
    if current_state not in _ALLOWED_TRIGGER_STATES:
        current_state = "inactive"

    rule = str(threshold_rule or "").strip().lower()
    prev_num = _safe_float(previous_value)
    value_num = _safe_float(value)

    if rule in {"", "manual"}:
        return current_state

    if rule.startswith("cross_above:"):
        target = _safe_float(rule.split(":", 1)[1])
        if target is not None and value_num is not None:
            if value_num >= target:
                return "confirmed"
            if prev_num is not None and prev_num < target and value_num < target:
                return "building"
            return "inactive"

    if rule.startswith("cross_below:"):
        target = _safe_float(rule.split(":", 1)[1])
        if target is not None and value_num is not None:
            if value_num <= target:
                return "confirmed"
            if prev_num is not None and prev_num > target and value_num > target:
                return "building"
            return "inactive"

    if rule == "two_consecutive_improvements":
        if prev_num is None or value_num is None:
            return "early_watch"
        if value_num > prev_num:
            if current_state in {"early_watch", "building"}:
                return "confirmed"
            return "building"
        if value_num < prev_num:
            return "broken"
        return current_state

    if rule == "two_consecutive_deteriorations":
        if prev_num is None or value_num is None:
            return "early_watch"
        if value_num < prev_num:
            if current_state in {"early_watch", "building"}:
                return "confirmed"
            return "building"
        if value_num > prev_num:
            return "broken"
        return current_state

    return current_state


def _trigger_matches_feed(trigger: Dict[str, Any], feed_id: str) -> bool:
    fid = str(feed_id or "").strip()
    if not fid:
        return False

    # preferred
    t_feed_id = str(trigger.get("feed_id") or "").strip()
    if t_feed_id and t_feed_id == fid:
        return True

    # tolerated aliases
    t_data_source_id = str(trigger.get("data_source_id") or "").strip()
    if t_data_source_id and t_data_source_id == fid:
        return True

    t_source_feed_id = str(trigger.get("source_feed_id") or "").strip()
    if t_source_feed_id and t_source_feed_id == fid:
        return True

    # last resort legacy (often human label; only match if it literally equals feed_id)
    t_data_source = str(trigger.get("data_source") or "").strip()
    if t_data_source and t_data_source == fid:
        return True

    return False


def _get_trigger_list_and_key(trigger_map: Dict[str, Any]) -> tuple[list, str]:
    """
    Your trigger-map store uses 'trigger_entries' (seen in ULVR file),
    but some older code uses 'triggers'. Support both and write back to the same key.
    """
    if isinstance(trigger_map.get("triggers"), list):
        return trigger_map["triggers"], "triggers"
    if isinstance(trigger_map.get("trigger_entries"), list):
        return trigger_map["trigger_entries"], "trigger_entries"
    return [], "trigger_entries"


class LiveVariableTracker:
    """
    Bridges feed updates into company trigger-map state.

    IMPORTANT:
      Trigger maps must carry a machine routing key per entry (feed_id / source_feed_id / data_source_id).
      'data_source' is treated as a human label.
    """

    def __init__(
        self,
        *,
        trigger_map_store: CompanyTriggerMapStore,
        feed_registry: FeedRegistry,
        observers: Optional[List[Callable[[Dict[str, Any]], None]]] = None,
    ):
        self.trigger_map_store = trigger_map_store
        self.feed_registry = feed_registry
        self._company_variable_history: Dict[str, List[Dict[str, Any]]] = {}
        self.observers: List[Callable[[Dict[str, Any]], None]] = list(observers or [])

    def get_company_variable_history(self, company_ref: str) -> List[Dict[str, Any]]:
        return deepcopy(self._company_variable_history.get(company_ref, []))

    def track_feed_value(
        self,
        *,
        feed_id: str,
        value: Any,
        as_of: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        feed = self.feed_registry.get_feed(feed_id)
        if not feed:
            raise KeyError(f"Unknown feed_id: {feed_id}")

        as_of = as_of or _utc_now_iso()
        metadata = deepcopy(metadata or {})

        affected_maps = self.trigger_map_store.list_trigger_maps_by_feed(feed_id)
        updates: List[Dict[str, Any]] = []

        for trigger_map in affected_maps:
            trigger_map_id = trigger_map.get("company_trigger_map_id")
            company_ref = trigger_map.get("company_ref")
            if not trigger_map_id or not company_ref:
                continue

            triggers, _key = _get_trigger_list_and_key(trigger_map)
            if not triggers:
                continue

            changed = False

            for trigger in triggers:
                if not isinstance(trigger, dict):
                    continue
                if not _trigger_matches_feed(trigger, feed_id):
                    continue

                previous_value = trigger.get("latest_value")
                previous_state = trigger.get("current_state", "inactive")

                new_state = _infer_trigger_state(
                    current_state=previous_state,
                    threshold_rule=trigger.get("threshold_rule", ""),
                    previous_value=previous_value,
                    value=value,
                )

                trigger["latest_value"] = value
                trigger["last_updated_at"] = as_of
                trigger["current_state"] = new_state
                trigger.setdefault("update_history", []).append(
                    {
                        "as_of": as_of,
                        "feed_id": feed_id,
                        "value": value,
                        "previous_state": previous_state,
                        "new_state": new_state,
                        "metadata": deepcopy(metadata),
                    }
                )
                changed = True

                updates.append(
                    {
                        "company_ref": company_ref,
                        "trigger_map_id": trigger_map_id,
                        "trigger_id": trigger.get("trigger_id"),
                        "feed_id": feed_id,
                        "value": value,
                        "state": new_state,
                    }
                )

            if changed:
                self.trigger_map_store.save_trigger_map_payload(trigger_map, validate=False)
                self._company_variable_history.setdefault(company_ref, []).append(
                    {"as_of": as_of, "feed_id": feed_id, "value": value, "metadata": deepcopy(metadata)}
                )

        event = {
            "feed_id": feed_id,
            "as_of": as_of,
            "value": value,
            "metadata": deepcopy(metadata),
            "affected_trigger_maps": sorted({u["trigger_map_id"] for u in updates}),
            "updates": deepcopy(updates),
        }

        for cb in self.observers:
            try:
                cb(deepcopy(event))
            except Exception:
                pass

        return event


__all__ = ["LiveVariableTracker"]