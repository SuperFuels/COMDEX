# backend/modules/lean/lean_exporter_stub.py
# -*- coding: utf-8 -*-
"""Lean Exporter (Stub) - compatibility layer for SRK-8.

Only keep this if something still imports these names.
Otherwise delete this file and fix imports.
"""

def export_axioms_to_lean(*args, **kwargs):
    print("[LeanExporterStub] export_axioms_to_lean called (stub).")
    return True

def normalize_theorem(*args, **kwargs):
    print("[LeanExporterStub] normalize_theorem called (stub).")
    return True