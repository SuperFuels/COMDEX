# backend/modules/tests/test_fuzz_registry_cpu.py
import io
import sys
import os
import json
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from backend.codexcore_virtual.cpu_executor import VirtualCPU
from backend.core.registry_bridge import registry_bridge


# Configure fuzzing depth via env var
MAX_EXAMPLES = int(os.getenv("FUZZ_MAX_EXAMPLES", "50"))  # CI default = 50


# Utility: capture stdout manually
class CaptureStdout:
    def __enter__(self):
        self._old = sys.stdout
        sys.stdout = self._buf = io.StringIO()
        return self._buf

    def __exit__(self, *a):
        sys.stdout = self._old


def extract_logs(output: str):
    """Parse [LOG] lines into JSON dicts."""
    logs = []
    for line in output.splitlines():
        if line.startswith("[LOG]"):
            try:
                logs.append(json.loads(line[len("[LOG] "):]))
            except Exception:
                pass
    return logs


@given(
    program=st.lists(
        st.sampled_from(["LOG", "FAKE_OP", "teleport"]),
        min_size=1,
        max_size=5
    )
)
@settings(
    max_examples=MAX_EXAMPLES,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_fuzz_random_programs(program):
    cpu = VirtualCPU()
    cpu.load_program([f"{op} test" for op in program])

    with CaptureStdout() as buf:
        try:
            cpu.run()
        except Exception:
            pass

    logs = extract_logs(buf.getvalue())
    assert isinstance(logs, list)
    assert all("event" in log for log in logs)


@given(
    op=st.sampled_from(["glyph:log", "glyph:teleport", "core:⊕", "fake:op"]),
    arg=st.text()
)
@settings(
    max_examples=MAX_EXAMPLES,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_fuzz_direct_bridge(op, arg):
    with CaptureStdout() as buf:
        try:
            registry_bridge.resolve_and_execute(op, arg)
        except Exception:
            pass

    logs = extract_logs(buf.getvalue())
    assert isinstance(logs, list)
    assert all("event" in log for log in logs)