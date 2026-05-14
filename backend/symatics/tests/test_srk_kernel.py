# backend/symatics/tests/test_srk_kernel.py
import pytest
from backend.symatics.core.srk_kernel import SymaticsReasoningKernel

def test_basic_operator_flow():
    srk = SymaticsReasoningKernel()
    a, b = 1.0, 2.0
    result = srk.superpose(a, b)
    assert result is not None

def test_diagnostics_summary():
    srk = SymaticsReasoningKernel()
    summary = srk.diagnostics()
    assert "operators" in summary
    assert "laws" in summary
    assert "trace_count" in summary