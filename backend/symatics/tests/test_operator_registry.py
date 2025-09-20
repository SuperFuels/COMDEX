# backend/symatics/tests/test_operator_registry.py
import importlib
import pkgutil
import inspect
import os
import pathlib

import pytest

import symatics.operators as operators
from symatics.operators import Operator, OPS


def test_all_operator_files_registered():
    """
    Ensure that every *_op defined in symatics/operators/*.py
    is imported and registered in OPS.
    """
    pkg_path = pathlib.Path(operators.__file__).parent

    missing = []

    for _, module_name, ispkg in pkgutil.iter_modules([str(pkg_path)]):
        if ispkg or module_name == "__init__":
            continue

        mod = importlib.import_module(f"symatics.operators.{module_name}")

        # Find all Operator instances in this module
        for name, obj in inspect.getmembers(mod):
            if isinstance(obj, Operator):
                if obj not in OPS.values():
                    missing.append((module_name, name))

    assert not missing, f"Operators not registered in OPS: {missing}"


def test_ops_consistency():
    """
    Sanity check: OPS keys and Operator names should agree.
    """
    for symbol, op in OPS.items():
        assert isinstance(op, Operator)
        assert op.name == symbol, f"OPS mismatch: {symbol} vs {op.name}"