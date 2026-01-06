# /workspaces/COMDEX/backend/modules/sqi/sqi_container_registry.py
# Minimal, UCS-friendly registry for SQI + priority scoring (CR8)
#
# pytest / determinism goals:
# - NO import-time runtime bring-up / KG writes
# - NO wall-clock dependence when TESSARIS_DETERMINISTIC_TIME=1
# - NO noisy prints when TESSARIS_TEST_QUIET=1

from __future__ import annotations

import logging
import os
from datetime import datetime
from math import exp
from typing import Any, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)

# kept (may be used by downstream imports) but never required here
try:
    from backend.modules.codex.codex_trace import CodexTrace  # noqa: F401
except Exception:
    CodexTrace = None  # type: ignore

# --- Optional UCS address registry hook ------------------------------------
try:
    from backend.modules.dimensions.universal_container_system.address_registry import (
        register_container_address as _registry_register,
    )
except Exception:
    def _registry_register(*args, **kwargs):  # type: ignore
        return {}


def _deterministic_time_enabled() -> bool:
    return os.getenv("TESSARIS_DETERMINISTIC_TIME") == "1"


def _quiet_enabled() -> bool:
    return os.getenv("TESSARIS_TEST_QUIET") == "1"


def _utcnow() -> datetime:
    # Deterministic mode: no wall clock.
    return datetime(1970, 1, 1) if _deterministic_time_enabled() else datetime.utcnow()


SQI_NS = "ucs://knowledge"

# --- Scoring weights (legacy, used by _score) -------------------------------
_DEFAULT_WEIGHTS = {
    "domain_match": 2.0,   # same domain as goal
    "freshness":    1.0,   # recently updated
    "size_bias":   -0.5,   # penalize very large containers (spread out)
    "hot_flag":     1.5,   # meta.hot=True gets a boost
}


def _safe_registry_register(
    container_id: str,
    address: str,
    *,
    meta: Optional[Dict[str, Any]] = None,
    kind: str = "container",
) -> None:
    """
    Best-effort adapter for different register_container_address signatures.
    Supports either:
      - (cid, address, meta=..., kind=...)
      - (cid, address)
      - (cid, address, meta)
    """
    try:
        _registry_register(container_id, address, meta=meta or {}, kind=kind)
        return
    except TypeError:
        pass
    try:
        _registry_register(container_id, address)
        return
    except TypeError:
        pass
    try:
        _registry_register(container_id, address, meta or {})
        return
    except TypeError:
        return


def register_container(container: Union[Dict[str, Any], Any]) -> None:
    """
    Best-effort container registration + optional symbolic tree export.

    IMPORTANT:
    - No KG export / heavy imports unless explicitly enabled.
    - All side effects gated so tests stay clean.
    """
    # --- Step 1: Extract container ID safely ---
    if isinstance(container, dict):
        # validate_symbolic_fields can be heavy; import only when needed
        try:
            from backend.modules.validation.symbolic_container_validator import validate_symbolic_fields
        except Exception:
            validate_symbolic_fields = None  # type: ignore

        if callable(validate_symbolic_fields) and not validate_symbolic_fields(container):
            raise ValueError(
                "Symbolic container fields are out of sync (missing 'id', 'glyphs', or symbolic header)"
            )
        container_id = container.get("id") or container.get("containerId")
    else:
        container_id = getattr(container, "id", None)
        if not container_id and hasattr(container, "container_id"):
            container_id = getattr(container, "container_id")

    if not container_id:
        raise ValueError("Container is missing a valid 'id' or 'container_id'")

    # --- Step 2: Register with SQI symbolic container namespace (best-effort) ---
    addr = f"{SQI_NS}/containers/{container_id}"
    _safe_registry_register(container_id, addr, meta={"created_by": "SQI"}, kind="container")

    if not _quiet_enabled():
        logger.info(f"[SQIRegistry] registered container: {container_id} @ {addr}")

    # --- Step 3: Optional Symbolic Meaning Tree export (OFF by default) ---
    # Enable explicitly in runtime: SQI_AUTO_EXPORT_TREE=1
    if os.getenv("SQI_AUTO_EXPORT_TREE") != "1":
        return
    if _quiet_enabled() or _deterministic_time_enabled():
        # Never export during tests / deterministic runs.
        return

    try:
        from backend.modules.symbolic.symbol_tree_generator import build_tree_from_container, export_tree_to_kg
        tree = build_tree_from_container(container_id)
        if tree and getattr(tree, "root", None):
            export_tree_to_kg(tree)
            logger.info(f"[SQIRegistry] exported symbolic tree -> KG for: {container_id}")
        else:
            logger.warning(f"[SQIRegistry] empty symbolic tree for: {container_id}")
    except Exception as e:
        logger.warning(f"[SQIRegistry] tree export failed for {container_id}: {e}")


def _age_hours(iso: Optional[str]) -> float:
    """Convert ISO8601 to approximate age in hours. Missing/bad -> very old."""
    if not iso:
        return 1e9
    try:
        dt = datetime.fromisoformat(iso.replace("Z", ""))
        delta = _utcnow() - dt
        return max(0.0, delta.total_seconds() / 3600.0)
    except Exception:
        return 1e9


class SQIContainerRegistry:
    """
    Type-aware container allocator for SQI.
    Types: fact | project | note | hypothesis | simulation
    """

    # --- CR8 route weights (hot-tunable at runtime) -------------------------
    _route_weights = {
        "domain_match": 0.6,     # exact or prefix domain match
        "kind_match":   0.25,    # type/kind alignment
        "freshness":    0.10,    # newer last_updated preferred
        "priority_hint": 0.05,   # optional meta.priority boost
        "size_penalty": 0.00,    # optional negative weight (larger = worse)
    }

    def __init__(self):
        self.index: Dict[str, Dict[str, Any]] = {}  # cid -> entry
        self.by_domain: Dict[str, Set[str]] = {}    # "math.calculus" -> {cid,...}

    # --- addressing ---------------------------------------------------------
    def _addr(self, kind: str, domain: str, name: str) -> str:
        kind_map = {
            "fact": "facts",
            "project": "projects",
            "note": "notes",
            "hypothesis": "hypotheses",
            "simulation": "simulations",
        }
        k = kind_map.get(kind, kind)
        return f"{SQI_NS}/{k}/{domain}/{name}"

    # --- rehydrate from UCS on startup --------------------------------------
    def rehydrate_from_ucs(self) -> int:
        """
        Rebuild the in-memory registry from UCS runtime if available.
        """
        try:
            from backend.modules.dimensions.universal_container_system import ucs_runtime
        except Exception:
            return 0

        count = 0
        for cid, c in (getattr(ucs_runtime, "containers", {}) or {}).items():
            if not isinstance(c, dict):
                continue
            entry = {
                "id": cid,
                "type": "container",
                "kind": c.get("kind"),
                "domain": c.get("domain"),
                "meta": c.get("meta", {}),
            }
            self.index[cid] = entry
            if entry.get("domain"):
                self.by_domain.setdefault(entry["domain"], set()).add(cid)
            count += 1
        return count

    # --- allocate or upsert -------------------------------------------------
    def allocate(
        self,
        *,
        kind: str,
        domain: str,
        name: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create or update a minimal registry entry for a container; idempotent.
        """
        cid = name
        address = self._addr(kind, domain, name)
        now = _utcnow().isoformat() + ("Z" if not _deterministic_time_enabled() else "")

        ghx_meta = {"hover": True, "collapsed": True}
        if meta and isinstance(meta.get("ghx"), dict):
            ghx_meta.update(meta["ghx"])

        entry = {
            "id": cid,
            "type": "container",
            "kind": kind,
            "domain": domain,
            "meta": {
                "address": address,
                "created_by": "SQI",
                "last_updated": now,
                "ghx": ghx_meta,
                **(meta or {}),
            },
        }

        self.index[cid] = entry
        self.by_domain.setdefault(domain, set()).add(cid)

        try:
            _safe_registry_register(cid, address, meta=entry["meta"], kind="container")
        except Exception:
            pass

        return entry

    def upsert_meta(self, cid: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        if cid not in self.index:
            raise ValueError(f"Unknown SQI container: {cid}")

        entry = self.index[cid]
        current_meta = entry.get("meta", {}) or {}
        updated_meta = {**current_meta, **(patch or {})}

        updated_meta["last_updated"] = _utcnow().isoformat() + ("Z" if not _deterministic_time_enabled() else "")

        # Collapsibility state injection
        updated_meta.setdefault("collapsible", True)
        updated_meta.setdefault("default_state", "collapsed")

        updated_meta["state_flags"] = {
            "collapsed": updated_meta["default_state"] == "collapsed",
            "hover_preview": bool(updated_meta.get("hover_preview", False)),
        }

        ghx_meta = updated_meta.get("ghx", {}) or {}
        ghx_meta.setdefault("hover", True)
        ghx_meta.setdefault("collapsed", updated_meta["default_state"] == "collapsed")
        updated_meta["ghx"] = ghx_meta

        entry["meta"] = updated_meta
        return entry

    # --- lookups ------------------------------------------------------------
    def lookup_by_domain(self, domain: str) -> List[str]:
        return sorted(self.by_domain.get(domain, set()))

    def get(self, cid: str) -> Optional[Dict[str, Any]]:
        return self.index.get(cid)

    def evaluate_container(
        self,
        container: Union[Dict[str, Any], Any],
        goal: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not container:
            return {"sqi_score": 0.0, "reason": "empty"}

        goal = goal or {}

        if isinstance(container, dict):
            domain = container.get("domain")
            kind = container.get("kind")
            meta = container.get("meta", {}) or {}
        else:
            domain = getattr(container, "domain", None)
            kind = getattr(container, "kind", None)
            meta = getattr(container, "meta", None) or {}

        entry = {"domain": domain, "kind": kind, "meta": meta}

        score = self._score(entry, goal)
        hover = bool((entry["meta"].get("ghx", {}) or {}).get("hover", False))
        collapsed = bool((entry["meta"].get("ghx", {}) or {}).get("collapsed", True))

        return {
            "sqi_score": score,
            "domain_match": goal.get("domain") == entry.get("domain"),
            "age_hours": _age_hours(entry["meta"].get("last_updated")),
            "glyph_count": int(((entry["meta"].get("stats") or {}) or {}).get("glyphs", 0)),
            "ghx_hover": hover,
            "collapsed": collapsed,
        }

    # --- legacy scoring helper (kept for compatibility) ---------------------
    def _score(
        self,
        entry: Dict[str, Any],
        goal: Dict[str, Any],
        w: Optional[Dict[str, float]] = None,
    ) -> float:
        w = {**_DEFAULT_WEIGHTS, **(w or {})}
        meta = (entry.get("meta") or {})
        domain = entry.get("domain")
        last_updated = meta.get("last_updated")
        hot = bool(meta.get("hot"))
        size = int((meta.get("stats") or {}).get("glyphs", 0))

        domain_match = 1.0 if domain and goal.get("domain") == domain else 0.0

        age_h = _age_hours(last_updated)
        freshness = exp(-age_h / 72.0)

        size_term = size / 1000.0
        hot_term = 1.0 if hot else 0.0

        return (
            w["domain_match"] * domain_match
            + w["freshness"] * freshness
            + w["size_bias"] * size_term
            + w["hot_flag"] * hot_term
        )

    # --- CR8: tunable weights API -------------------------------------------
    def set_route_weights(self, **weights):
        for k, v in weights.items():
            if k in self._route_weights and isinstance(v, (int, float)):
                self._route_weights[k] = float(v)
        return dict(self._route_weights)

    # ---- selection API ------------------------------------------------------
    def choose_for(
        self,
        *,
        domain: str | None = None,
        topic: str | None = None,
        kind: str = "fact",
        meta: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        want_domain = (domain or topic or "") or ""
        cands = self._collect_candidates()
        if not cands:
            if not want_domain:
                raise ValueError("No domain/topic provided and no candidates available.")
            return self.allocate(kind=kind, domain=want_domain, name=want_domain, meta=meta)

        scored: List[tuple[float, Dict[str, Any]]] = []
        for e in cands:
            s = self._score_entry(e, want_domain=want_domain, want_kind=kind, topic=topic)
            scored.append((s, e))
        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored or scored[0][0] <= 0.0:
            if not want_domain:
                raise ValueError(f"No suitable container for kind='{kind}' and no domain given.")
            return self.allocate(kind=kind, domain=want_domain, name=want_domain, meta=meta)

        return scored[0][1]

    def _choose_for_topic(self, topic: str, kind: str = "fact", meta: Optional[Dict[str, Any]] = None, **kwargs):
        return self.choose_for(domain=topic, kind=kind, meta=meta, **kwargs)

    # ---- helpers ------------------------------------------------------------
    def _collect_candidates(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []

        # 1) entries we already hold
        for _, v in (self.index or {}).items():
            e = self._normalize_entry(v)
            if e:
                out.append(e)

        # 2) UCS runtime (if available)
        try:
            from backend.modules.dimensions.universal_container_system import ucs_runtime
            ids: List[str] = []

            if hasattr(ucs_runtime, "list_containers"):
                ids = ucs_runtime.list_containers()  # type: ignore
            elif hasattr(ucs_runtime, "registry"):
                ids = list(getattr(ucs_runtime, "registry", {}).keys())
            else:
                ids = list(getattr(ucs_runtime, "containers", {}).keys())

            for cid in ids or []:
                try:
                    uc = None
                    if hasattr(ucs_runtime, "get_container"):
                        uc = ucs_runtime.get_container(cid)
                    elif hasattr(ucs_runtime, "index"):
                        uc = ucs_runtime.index.get(cid)
                    elif hasattr(ucs_runtime, "registry"):
                        uc = ucs_runtime.registry.get(cid)
                    else:
                        uc = getattr(ucs_runtime, "containers", {}).get(cid)
                    if not uc:
                        continue
                    norm = self._normalize_entry(uc if isinstance(uc, dict) else {"id": cid, "meta": {}})
                    if norm:
                        out.append(norm)
                except Exception:
                    continue
        except Exception:
            pass

        uniq: Dict[str, Dict[str, Any]] = {}
        for e in out:
            eid = e.get("id")
            if eid and eid not in uniq:
                uniq[eid] = e
        return list(uniq.values())

    def _normalize_entry(self, raw: Dict[str, Any] | None) -> Optional[Dict[str, Any]]:
        if not isinstance(raw, dict):
            return None

        eid = raw.get("id") or raw.get("container_id")
        if not eid:
            return None

        domain = raw.get("domain") or (raw.get("meta", {}) or {}).get("domain")
        kind = raw.get("kind") or (raw.get("meta", {}) or {}).get("kind") or raw.get("type")

        meta = dict(raw.get("meta", {}) or {})

        ghx = meta.get("ghx") or {}
        ghx.setdefault("hover", True)
        ghx.setdefault("collapsed", True)
        meta["ghx"] = ghx

        if "address" not in meta:
            if domain and kind:
                meta["address"] = f"ucs://knowledge/{kind}s/{domain}/{eid}"
            else:
                meta["address"] = f"ucs://knowledge/{eid}"

        return {"id": eid, "domain": domain, "kind": kind, "meta": meta}

    def _score_entry(self, e: Dict[str, Any], *, want_domain: str, want_kind: str, topic: str | None) -> float:
        w = self._route_weights
        s = 0.0

        ed = (e.get("domain") or "") or ""
        if ed == want_domain:
            s += w["domain_match"] * 1.0
        elif want_domain and (ed.startswith(want_domain) or want_domain.startswith(ed)):
            s += w["domain_match"] * 0.6
        elif ed.split(".")[0:1] == want_domain.split(".")[0:1] and ed and want_domain:
            s += w["domain_match"] * 0.35

        if (e.get("kind") or "") == (want_kind or ""):
            s += w["kind_match"] * 1.0

        fresh = 0.0
        try:
            ts = (e.get("meta", {}) or {}).get("last_updated")
            if ts:
                dt = datetime.fromisoformat(ts.replace("Z", ""))
                age = (_utcnow() - dt).total_seconds()
                fresh = max(0.0, min(1.0, 1.0 - (age / (30 * 24 * 3600))))
        except Exception:
            pass
        s += w["freshness"] * fresh

        pri = float((e.get("meta", {}) or {}).get("priority", 0.0) or 0.0)
        s += w["priority_hint"] * max(0.0, min(1.0, pri))

        size = float((e.get("meta", {}) or {}).get("size", 0.0) or 0.0)
        s -= w["size_penalty"] * max(0.0, size)

        if topic:
            topics = (e.get("meta", {}) or {}).get("topics", [])
            if isinstance(topics, list) and topic in topics:
                s += 0.05

        return s


# ─────────────────────────────────────────────
# Lazy singleton (NO import-time bring-up)
# ─────────────────────────────────────────────
_REGISTRY: Optional[SQIContainerRegistry] = None


def get_sqi_registry() -> SQIContainerRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = SQIContainerRegistry()
        if not _quiet_enabled():
            logger.info("[SQIRegistry] initialized (lazy)")
    return _REGISTRY


# Back-compat: allow `from ... import sqi_registry` without triggering init.
class _RegistryProxy:
    def __getattr__(self, name: str):
        return getattr(get_sqi_registry(), name)


sqi_registry = _RegistryProxy()
