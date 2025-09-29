# -*- coding: utf-8 -*-
# File: backend/modules/tests/test_cpu_executor.py
"""
Test: Virtual CPU Executor Delegation
-------------------------------------
Validates that VirtualCPU routes all ops via the global
instruction_registry (no CPU hardcoding).
Covers:
  • Registry delegation with a fake op
  • Error handling for unknown ops
  • Register/memory behavior with MOV/STORE/PRINT
  • HALT stopping the CPU
"""

import pytest
import io
import sys

from backend.codexcore_virtual.cpu_executor import VirtualCPU
from backend.codexcore_virtual import instruction_registry as ir


def test_cpu_runs_registered_ops(monkeypatch):
    cpu = VirtualCPU()

    # Monkeypatch registry handler for a fake op
    called = {}

    def fake_handler(ctx, a=None, b=None, **kw):
        called["ctx"] = ctx
        called["a"] = a
        called["b"] = b
        return f"ADD({a},{b})"

    # Register fake op in registry
    ir.registry.override("logic:FAKE_ADD", fake_handler)
    ir.registry.alias("FAKE_ADD", "logic:FAKE_ADD")

    # Program with FAKE_ADD
    cpu.program = [{"operation": "FAKE_ADD", "args": [2, 3]}]
    cpu.running = True
    cpu.tick()

    assert called["ctx"] == cpu
    assert called["a"] == 2
    assert called["b"] == 3


def test_cpu_raises_on_unknown_op():
    cpu = VirtualCPU()
    cpu.program = [{"operation": "NON_EXISTENT", "args": []}]
    cpu.running = True

    with pytest.raises(ValueError) as e:
        cpu.tick()

    assert "Unknown instruction" in str(e.value)


def test_cpu_store_and_print(monkeypatch):
    cpu = VirtualCPU()

    # Handlers for MOV, STORE, PRINT
    def handle_mov(ctx, reg=None, value=None, **kw):
        ctx.registers[reg] = int(value)
        return f"[MOV] {reg}={value}"

    def handle_store(ctx, reg=None, addr=None, **kw):
        ctx.memory[addr] = ctx.registers.get(reg, None)
        return f"[STORE] {reg} -> {addr}"

    def handle_print(ctx, reg=None, **kw):
        print(f"[PRINT] {reg}={ctx.registers.get(reg)}")
        return ctx.registers.get(reg)

    # Register handlers
    ir.registry.override("logic:MOV", handle_mov)
    ir.registry.alias("MOV", "logic:MOV")

    ir.registry.override("logic:STORE", handle_store)
    ir.registry.alias("STORE", "logic:STORE")

    ir.registry.override("logic:PRINT", handle_print)
    ir.registry.alias("PRINT", "logic:PRINT")

    # Program: MOV → STORE → PRINT
    cpu.program = [
        {"operation": "MOV", "args": ["R1", 42]},
        {"operation": "STORE", "args": ["R1", "100"]},
        {"operation": "PRINT", "args": ["R1"]},
    ]

    # Capture stdout
    captured = io.StringIO()
    sys_stdout = sys.stdout
    sys.stdout = captured

    cpu.running = True
    while cpu.running:
        cpu.tick()

    sys.stdout = sys_stdout
    output = captured.getvalue()

    # Validate effects
    assert cpu.registers["R1"] == 42
    assert cpu.memory["100"] == 42
    assert "[PRINT] R1=42" in output


def test_cpu_halt_stops(monkeypatch):
    cpu = VirtualCPU()

    # HALT handler
    def handle_halt(ctx, **kw):
        ctx.running = False
        return "[HALT]"

    ir.registry.override("logic:HALT", handle_halt)
    ir.registry.alias("HALT", "logic:HALT")

    # Program: HALT immediately
    cpu.program = [{"operation": "HALT", "args": []}]

    cpu.running = True
    cpu.run()

    assert cpu.running is False