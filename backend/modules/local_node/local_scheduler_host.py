from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event, Lock, Thread
from typing import Any, Callable, Dict, List, Optional
import traceback

from backend.modules.local_node.contracts_local_node import utc_now_iso


@dataclass(slots=True)
class SchedulerTickResult:
    ok: bool
    did_work: bool
    status: str
    detail: Optional[str] = None
    at: str = field(default_factory=utc_now_iso)


class LocalSchedulerHost:
    """
    Local scheduler host.

    Responsibilities:
    - heartbeat every N seconds
    - single manual tick execution
    - optional background loop
    - skip execution when node is paused/stopped
    - keep node state fresh
    - write scheduler audit events
    - scan due triggers on each tick
    - fire scheduled workflows safely
    """

    def __init__(
        self,
        *,
        heartbeat_interval_seconds: int,
        get_control_status: Callable[[], Dict[str, Any]],
        heartbeat_fn: Callable[[], Dict[str, Any]],
        run_next_fn: Callable[[], Dict[str, Any]],
        append_audit_fn: Callable[..., None],
        list_due_triggers_fn: Optional[Callable[[str], List[Dict[str, Any]]]] = None,
        fire_trigger_fn: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> None:
        self.heartbeat_interval_seconds = max(1, int(heartbeat_interval_seconds))
        self.get_control_status = get_control_status
        self.heartbeat_fn = heartbeat_fn
        self.run_next_fn = run_next_fn
        self.append_audit_fn = append_audit_fn

        self.list_due_triggers_fn = list_due_triggers_fn
        self.fire_trigger_fn = fire_trigger_fn

        self._thread: Optional[Thread] = None
        self._stop_event = Event()
        self._lock = Lock()

        self._is_running = False
        self._last_tick_at: Optional[str] = None
        self._last_tick_result: Optional[Dict[str, Any]] = None
        self._last_error: Optional[str] = None
        self._started_at: Optional[str] = None
        self._stopped_at: Optional[str] = None

    def _append_audit(
        self,
        *,
        event_type: str,
        message: str,
        payload: Optional[Dict[str, Any]] = None,
        level: str = "info",
    ) -> None:
        try:
            self.append_audit_fn(
                event_type=event_type,
                message=message,
                payload=payload or {},
                level=level,
            )
        except Exception:
            pass

    def _control_status_value(self) -> str:
        try:
            control = self.get_control_status() or {}
            return str(control.get("status") or "unknown")
        except Exception:
            return "unknown"

    def _summarize_heartbeat(self, heartbeat_result: Dict[str, Any]) -> Dict[str, Any]:
        health = heartbeat_result.get("health") or {}
        status = health.get("status")
        if not status:
            status = (
                (heartbeat_result.get("control") or {}).get("status")
                or heartbeat_result.get("status")
                or "unknown"
            )

        at = (
            health.get("last_heartbeat_at")
            or (heartbeat_result.get("state") or {}).get("heartbeat", {}).get("last_heartbeat_at")
            or heartbeat_result.get("at")
            or utc_now_iso()
        )

        return {
            "status": str(status),
            "at": str(at),
        }

    def _summarize_run_result(self, run_result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ok": bool(run_result.get("ok", True)),
            "did_work": bool(run_result.get("did_work", False)),
            "status": str(run_result.get("status") or "idle"),
            "at": str(run_result.get("at") or utc_now_iso()),
        }

    def _list_due_triggers(self, now_iso: str) -> List[Dict[str, Any]]:
        if not callable(self.list_due_triggers_fn):
            return []

        try:
            items = self.list_due_triggers_fn(now_iso) or []
            return [item for item in items if isinstance(item, dict)]
        except Exception as exc:
            self._append_audit(
                event_type="local_node.scheduler_trigger_scan_failed",
                message="Due trigger scan failed",
                payload={"error": str(exc)},
                level="error",
            )
            return []

    def _fire_due_triggers(
        self,
        due_triggers: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not due_triggers or not callable(self.fire_trigger_fn):
            return []

        results: List[Dict[str, Any]] = []

        for trigger in due_triggers:
            trigger_id = str(trigger.get("id") or "")
            trigger_name = str(trigger.get("name") or trigger_id or "trigger")

            try:
                result = self.fire_trigger_fn(trigger) or {}
                normalized = {
                    "trigger_id": trigger_id,
                    "trigger_name": trigger_name,
                    "ok": bool(result.get("ok", True)),
                    "status": str(result.get("status") or "fired"),
                    "detail": result.get("detail"),
                    "run_id": result.get("run_id"),
                    "at": str(result.get("at") or utc_now_iso()),
                }
                results.append(normalized)

                self._append_audit(
                    event_type="local_node.scheduler_trigger_fired",
                    message="Scheduled trigger fired",
                    payload=normalized,
                    level="info" if normalized["ok"] else "error",
                )
            except Exception as exc:
                tb = traceback.format_exc()
                normalized = {
                    "trigger_id": trigger_id,
                    "trigger_name": trigger_name,
                    "ok": False,
                    "status": "error",
                    "detail": str(exc),
                    "at": utc_now_iso(),
                }
                results.append(normalized)

                self._append_audit(
                    event_type="local_node.scheduler_trigger_failed",
                    message="Scheduled trigger firing failed",
                    payload={
                        **normalized,
                        "traceback": tb,
                    },
                    level="error",
                )

        return results

    def tick(self) -> Dict[str, Any]:
        with self._lock:
            control_status = self._control_status_value()
            heartbeat_result = self.heartbeat_fn()
            heartbeat_summary = self._summarize_heartbeat(heartbeat_result)

            if control_status in {"paused", "stopped"}:
                result = {
                    "ok": True,
                    "did_work": False,
                    "status": "skipped",
                    "detail": f"Scheduler skipped because node is {control_status}",
                    "heartbeat": heartbeat_summary,
                    "trigger_scan": {
                        "count": 0,
                        "items": [],
                    },
                    "run_result": {
                        "ok": True,
                        "did_work": False,
                        "status": "skipped",
                        "at": utc_now_iso(),
                    },
                    "at": utc_now_iso(),
                }
                self._last_tick_at = result["at"]
                self._last_tick_result = result
                self._last_error = None

                self._append_audit(
                    event_type="local_node.scheduler_tick_skipped",
                    message="Scheduler tick skipped",
                    payload={"control_status": control_status},
                )
                return result

            try:
                now_iso = utc_now_iso()
                due_triggers = self._list_due_triggers(now_iso)
                trigger_results = self._fire_due_triggers(due_triggers)

                run_result = self.run_next_fn()
                run_summary = self._summarize_run_result(run_result)

                trigger_did_work = any(item.get("ok") for item in trigger_results)
                queue_did_work = bool(run_result.get("did_work", False))

                result = {
                    "ok": bool(run_result.get("ok", True)) and all(
                        item.get("ok", False) for item in trigger_results
                    )
                    if trigger_results
                    else bool(run_result.get("ok", True)),
                    "did_work": bool(trigger_did_work or queue_did_work),
                    "status": str(
                        run_result.get("status")
                        or ("triggered" if trigger_did_work else "idle")
                    ),
                    "detail": run_result.get("detail"),
                    "run_result": run_summary,
                    "trigger_scan": {
                        "count": len(due_triggers),
                        "items": trigger_results,
                    },
                    "heartbeat": heartbeat_summary,
                    "at": utc_now_iso(),
                }
                self._last_tick_at = result["at"]
                self._last_tick_result = result
                self._last_error = None

                self._append_audit(
                    event_type="local_node.scheduler_tick",
                    message="Scheduler tick executed",
                    payload={
                        "did_work": result["did_work"],
                        "status": result["status"],
                        "detail": result.get("detail"),
                        "due_trigger_count": len(due_triggers),
                        "trigger_fired_count": sum(
                            1 for item in trigger_results if item.get("ok")
                        ),
                        "queue_did_work": queue_did_work,
                    },
                )
                return result
            except Exception as exc:
                tb = traceback.format_exc()
                self._last_error = str(exc)

                result = {
                    "ok": False,
                    "did_work": False,
                    "status": "error",
                    "detail": str(exc),
                    "heartbeat": heartbeat_summary,
                    "trigger_scan": {
                        "count": 0,
                        "items": [],
                    },
                    "at": utc_now_iso(),
                }
                self._last_tick_at = result["at"]
                self._last_tick_result = result

                self._append_audit(
                    event_type="local_node.scheduler_tick_failed",
                    message="Scheduler tick failed",
                    payload={"error": str(exc), "traceback": tb},
                    level="error",
                )
                return result

    def _run_loop(self) -> None:
        self._append_audit(
            event_type="local_node.scheduler_loop_started",
            message="Scheduler background loop started",
            payload={"heartbeat_interval_seconds": self.heartbeat_interval_seconds},
        )

        while not self._stop_event.is_set():
            self.tick()
            self._stop_event.wait(self.heartbeat_interval_seconds)

        self._append_audit(
            event_type="local_node.scheduler_loop_stopped",
            message="Scheduler background loop stopped",
            payload={},
        )

    def start(self) -> Dict[str, Any]:
        with self._lock:
            if self._is_running and self._thread and self._thread.is_alive():
                return self.status()

            self._stop_event.clear()
            self._thread = Thread(
                target=self._run_loop,
                name="local-node-scheduler",
                daemon=True,
            )
            self._thread.start()

            self._is_running = True
            self._started_at = utc_now_iso()
            self._stopped_at = None
            self._last_error = None

            self._append_audit(
                event_type="local_node.scheduler_started",
                message="Scheduler started",
                payload={"started_at": self._started_at},
            )

            return self.status()

    def stop(self) -> Dict[str, Any]:
        with self._lock:
            thread = self._thread
            self._stop_event.set()

        if thread and thread.is_alive():
            thread.join(timeout=max(1, self.heartbeat_interval_seconds + 1))

        with self._lock:
            self._is_running = False
            self._stopped_at = utc_now_iso()

            self._append_audit(
                event_type="local_node.scheduler_stopped",
                message="Scheduler stopped",
                payload={"stopped_at": self._stopped_at},
            )

            return self.status()

    def status(self) -> Dict[str, Any]:
        thread_alive = bool(self._thread and self._thread.is_alive())

        return {
            "ok": True,
            "scheduler": {
                "is_running": self._is_running and thread_alive,
                "thread_alive": thread_alive,
                "heartbeat_interval_seconds": self.heartbeat_interval_seconds,
                "started_at": self._started_at,
                "stopped_at": self._stopped_at,
                "last_tick_at": self._last_tick_at,
                "last_tick_result": self._last_tick_result,
                "last_error": self._last_error,
                "control_status": self._control_status_value(),
                "trigger_support_enabled": callable(self.list_due_triggers_fn)
                and callable(self.fire_trigger_fn),
            },
            "at": utc_now_iso(),
        }