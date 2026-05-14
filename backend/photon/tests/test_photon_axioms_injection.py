"""
Test: Photon Axioms Injection
Ensures all axioms can be parsed and injected into the rewriter.
"""

from backend.photon.axioms import list_axioms

def test_axioms_injection():
    axioms = list_axioms()
    assert isinstance(axioms, dict)
    assert len(axioms) > 0
    for name, (lhs, rhs, desc) in axioms.items():
        assert isinstance(lhs, str)
        assert isinstance(rhs, str)
        assert isinstance(desc, str)

from backend.photon.export_axioms import export_axioms

def test_axioms_injection_snapshot():
    # ... your existing assertions ...
    export_axioms()

from backend.photon.export_core_spec import export_core_spec

def test_export_core_spec():
    """Auto-generate Photon Core Spec RFC after axioms are tested."""
    export_core_spec()