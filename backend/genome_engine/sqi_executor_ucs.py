from __future__ import annotations

from typing import Any, Dict, List
import contextlib
import io
import os


def _is_quiet() -> bool:
    # Prefer shared helper if present; fall back to env.
    try:
        from backend.utils.quiet import is_quiet  # type: ignore

        return bool(is_quiet())
    except Exception:
        return str(os.getenv("TESSARIS_TEST_QUIET", "0")).strip() in ("1", "true", "yes", "y", "on")


@contextlib.contextmanager
def _maybe_suppress_output(enabled: bool):
    if not enabled:
        yield
        return
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
        yield


def run_sqi_fabric_plan_ucs(
    *,
    plan: Dict[str, Any],
    scenario_summaries: Dict[str, Any],
    kg_write: bool,
) -> Dict[str, Any]:
    """
    UCS-gated SQI fabric executor.

    MVP:
      - materialize UCS containers best-effort
      - then reuse deterministic local executor for actual fabric output
      - never require servers
    """
    materialized: List[str] = []
    materialize_error: str | None = None

    quiet = _is_quiet()

    # (A) UCS materialize (best-effort; never hard-fail GX1)
    try:
        with _maybe_suppress_output(quiet):
            from backend.modules.sqi.sqi_container_registry import SQIContainerRegistry  # type: ignore
            from backend.modules.sqi.sqi_materializer import materialize_entry  # type: ignore

            reg = (
                SQIContainerRegistry.get_instance()
                if hasattr(SQIContainerRegistry, "get_instance")
                else SQIContainerRegistry()
            )

            jobs = plan.get("jobs") or []
            if isinstance(jobs, list):
                for j in jobs:
                    if not isinstance(j, dict):
                        continue
                    domain = str(j.get("domain") or j.get("topic") or "unknown")
                    kind = str(j.get("kind") or j.get("container_kind") or "fact")
                    name = str(j.get("name") or j.get("container_id") or j.get("id") or j.get("job_id") or domain)

                    entry = reg.allocate(kind=kind, domain=domain, name=name, meta={"source": "sqi_executor_ucs"})
                    snap = materialize_entry(entry)
                    cid = snap.get("id") if isinstance(snap, dict) else None
                    materialized.append(str(cid or name))

    except Exception as e:
        materialize_error = f"{type(e).__name__}: {e}"
        materialized = []

    # (B) Deterministic fabric result = local executor (canonical output)
    from .sqi_fabric_runner import run_sqi_fabric_plan_local

    local = run_sqi_fabric_plan_local(plan=plan, scenario_summaries=scenario_summaries, kg_write=kg_write)
    out: Dict[str, Any] = dict(local) if isinstance(local, dict) else {"local_result": local}

    # (C) UCS anchors
    uniq = sorted(set(materialized))
    out["executor"] = "ucs"
    out["ucs"] = {"materialized_containers": uniq, "materialized_count": int(len(uniq))}
    if materialize_error:
        out["ucs"]["materialize_error"] = materialize_error

    return out
