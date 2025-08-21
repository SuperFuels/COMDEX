import sys
import json
import datetime
from typing import Optional

# ANSI escape codes for terminal colors
LOG_COLORS = {
    "INFO": "\033[94m",     # Blue
    "WARN": "\033[93m",     # Yellow
    "ERROR": "\033[91m",    # Red
    "DEBUG": "\033[90m",    # Gray
    "RESET": "\033[0m",     # Reset
}

# Optional: Integrate with CodexMetrics
try:
    from backend.modules.codex.codex_metrics import CodexMetrics
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False


def _get_timestamp() -> str:
    return datetime.datetime.utcnow().isoformat()


def _format_message(level: str, message: str) -> str:
    color = LOG_COLORS.get(level, "")
    reset = LOG_COLORS["RESET"]
    return f"{color}[{level}] {_get_timestamp()} :: {message}{reset}"


def log_info(message: str, trace_id: Optional[str] = None, container: Optional[dict] = None):
    print(_format_message("INFO", message))
    _record_metrics("info", message, trace_id)
    _inject_into_container(container, "info", message)


def log_warn(message: str, trace_id: Optional[str] = None, container: Optional[dict] = None):
    print(_format_message("WARN", message), file=sys.stderr)
    _record_metrics("warn", message, trace_id)
    _inject_into_container(container, "warn", message)


def log_error(message: str, trace_id: Optional[str] = None, container: Optional[dict] = None):
    print(_format_message("ERROR", message), file=sys.stderr)
    _record_metrics("error", message, trace_id)
    _inject_into_container(container, "error", message)


def log_debug(message: str, trace_id: Optional[str] = None, container: Optional[dict] = None):
    print(_format_message("DEBUG", message))
    _record_metrics("debug", message, trace_id)
    _inject_into_container(container, "debug", message)


def _record_metrics(level: str, message: str, trace_id: Optional[str]):
    if METRICS_AVAILABLE:
        CodexMetrics.record_log_event(level=level, message=message, trace_id=trace_id)


def _inject_into_container(container: Optional[dict], level: str, message: str):
    if container is None:
        return

    trace_entry = {
        "type": "log",
        "level": level,
        "message": message,
        "timestamp": _get_timestamp(),
    }

    if "trace" not in container:
        container["trace"] = []

    container["trace"].append(trace_entry)


# Optional: Export logs to file
def save_log_to_file(log_entries: list, out_path: str):
    with open(out_path, "w") as f:
        json.dump(log_entries, f, indent=2)