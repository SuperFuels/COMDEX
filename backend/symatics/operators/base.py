# backend/symatics/operators/base.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Operator:
    """
    Core operator definition for Symatics algebra.

    Attributes
    ----------
    name : str
        Unicode symbol of the operator (⊕, ⋈, ↯, ⟲, etc.).
    arity : int
        Number of required arguments.
    impl : Callable[..., Any]
        Callable implementing the operator’s semantics.

    Notes
    -----
    - All concrete operators (superpose, fuse, resonance, etc.)
      should export an `Operator` instance defined with this base.
    - Arity validation is enforced by the dispatcher in `operators.py`.
    """
    name: str
    arity: int
    impl: Callable[..., Any]