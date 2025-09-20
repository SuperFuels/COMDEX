from __future__ import annotations
from dataclasses import dataclass
from typing import List, Union, Any

@dataclass(frozen=True)
class Var:
    name: str

@dataclass(frozen=True)
class Sym:
    name: str  # e.g., "⊕","↔","μ","⟲","π","𝔽","𝔼","τ","⊖"

@dataclass(frozen=True)
class App:
    head: Union[Sym,"App"]
    args: List["Term"]

Term = Union[Var, Sym, App]