# File: backend/modules/benchmark/real_qubit_simulator.py

import time
import random
from ..codex.codex_metrics import log_metric

def simulate_real_qubit_execution(depth: int = 5) -> float:
    """
    Simulates execution time of a real quantum computer for a circuit of given depth.
    For comparison purposes only — not physically accurate.
    """
    # Base time per gate in ns on real hardware (approximate)
    base_gate_time_ns = 500  # 0.5 microseconds per gate
    total_gates = 2 ** depth  # naive expansion

    simulated_time_ns = base_gate_time_ns * total_gates
    simulated_time_s = simulated_time_ns / 1_000_000_000

    # Simulate actual delay
    time.sleep(min(simulated_time_s, 0.01))  # cap at 10ms for testing

    return simulated_time_s


def compare_qglyph_to_qubit(qglyph_exec_time: float, depth: int = 5) -> dict:
    """
    Compares symbolic QGlyph execution with real quantum timing simulation.
    """
    qubit_time = simulate_real_qubit_execution(depth)
    speedup = qubit_time / qglyph_exec_time if qglyph_exec_time > 0 else float('inf')

    result = {
        "depth": depth,
        "qglyph_time": qglyph_exec_time,
        "qubit_time": qubit_time,
        "compression_speedup": speedup
    }

    log_metric("qglyph_vs_qubit", result)
    return result