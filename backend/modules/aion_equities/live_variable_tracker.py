# /workspaces/COMDEX/backend/modules/aion_equities/live_variable_tracker.py
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

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
    # match the rest of equities runtime (+00:00, no microseconds)
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, bool):
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
    if t_feed_id == fid:
        return True

    # tolerated aliases
    t_data_source_id = str(trigger.get("data_source_id") or "").strip()
    if t_data_source_id == fid:
        return True

    t_source_feed_id = str(trigger.get("source_feed_id") or "").strip()
    if t_source_feed_id == fid:
        return True

    # last resort legacy (human label; only match if it literally equals feed_id)
    t_data_source = str(trigger.get("data_source") or "").strip()
    if t_data_source == fid:
        return True

    return False


def _get_trigger_list_and_key(trigger_map: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    """
    Canonical is 'trigger_entries'. Some legacy payloads use 'triggers'.
    Prefer trigger_entries when both exist.
    """
    if isinstance(trigger_map.get("trigger_entries"), list):
        return trigger_map["trigger_entries"], "trigger_entries"
    if isinstance(trigger_map.get("triggers"), list):
        return trigger_map["triggers"], "triggers"
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

    # -----------------------------
    # store compat helpers
    # -----------------------------
    def _load_trigger_map_payload_any(
        self,
        *,
        trigger_map_stub: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        list_trigger_maps_by_feed() may return a stub (no trigger_entries). Always hydrate if possible.
        """
        store = self.trigger_map_store
        if not isinstance(trigger_map_stub, dict):
            return None

        # already hydrated
        if isinstance(trigger_map_stub.get("trigger_entries"), list) or isinstance(trigger_map_stub.get("triggers"), list):
            return trigger_map_stub

        tm_id = str(trigger_map_stub.get("company_trigger_map_id") or "").strip()
        company_ref = str(trigger_map_stub.get("company_ref") or "").strip()
        fiscal_period_ref = str(trigger_map_stub.get("fiscal_period_ref") or "").strip()

        # 1) load by id
        for fn_name in ("load_company_trigger_map_by_id",):
            fn = getattr(store, fn_name, None)
            if callable(fn) and tm_id:
                try:
                    payload = fn(tm_id)
                    if isinstance(payload, dict):
                        return payload
                except Exception:
                    pass

        # 2) load by (company_ref, fiscal_period_ref)
        for fn_name in ("load_company_trigger_map", "load_trigger_map"):
            fn = getattr(store, fn_name, None)
            if callable(fn) and company_ref and fiscal_period_ref:
                try:
                    payload = fn(company_ref=company_ref, fiscal_period_ref=fiscal_period_ref)
                    if isinstance(payload, dict):
                        return payload
                except Exception:
                    pass

        return None

    def _save_trigger_map_payload_any(self, payload: Dict[str, Any]) -> bool:
        """
        Compatibility saver across store versions.
        """
        store = self.trigger_map_store

        for fn_name in ("save_trigger_map_payload", "save_company_trigger_map_payload"):
            fn = getattr(store, fn_name, None)
            if callable(fn):
                try:
                    fn(payload, validate=False)
                    return True
                except Exception:
                    pass

        # fallback: if store only supports save_company_trigger_map(...)
        fn = getattr(store, "save_company_trigger_map", None)
        if callable(fn):
            try:
                company_ref = str(payload.get("company_ref") or "").strip()
                fiscal_period_ref = str(payload.get("fiscal_period_ref") or "").strip()
                triggers, key = _get_trigger_list_and_key(payload)
                if company_ref and fiscal_period_ref and isinstance(triggers, list):
                    fn(
                        company_ref=company_ref,
                        fiscal_period_ref=fiscal_period_ref,
                        trigger_entries=deepcopy(triggers),
                        generated_by="aion_equities.live_variable_tracker",
                        validate=False,
                        linked_refs_patch=deepcopy(payload.get("linked_refs") or {}),
                    )
                    return True
            except Exception:
                pass

        return False

    # -----------------------------
    # main entrypoint
    # -----------------------------
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

        affected = self.trigger_map_store.list_trigger_maps_by_feed(feed_id)
        updates: List[Dict[str, Any]] = []

        for stub in affected or []:
            payload = self._load_trigger_map_payload_any(trigger_map_stub=stub)
            if not isinstance(payload, dict):
                continue

            trigger_map_id = str(payload.get("company_trigger_map_id") or "").strip()
            company_ref = str(payload.get("company_ref") or "").strip()
            if not trigger_map_id or not company_ref:
                continue

            triggers, key = _get_trigger_list_and_key(payload)
            if not isinstance(triggers, list) or not triggers:
                continue

            changed = False

            for trigger in triggers:
                if not isinstance(trigger, dict):
                    continue
                if not _trigger_matches_feed(trigger, feed_id):
                    continue

                previous_value = trigger.get("latest_value")
                previous_state = str(trigger.get("current_state") or "inactive")

                new_state = _infer_trigger_state(
                    current_state=previous_state,
                    threshold_rule=trigger.get("threshold_rule", ""),
                    previous_value=previous_value,
                    value=value,
                )

                trigger["latest_value"] = value
                trigger["last_updated_at"] = as_of
                trigger["current_state"] = new_state

                hist = trigger.get("update_history")
                if not isinstance(hist, list):
                    hist = []
                    trigger["update_history"] = hist

                hist.append(
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
                # ensure we keep the same key we loaded (trigger_entries vs triggers)
                payload[key] = triggers
                if key == "trigger_entries":
                    payload.pop("triggers", None)

                ok = self._save_trigger_map_payload_any(payload)
                if ok:
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