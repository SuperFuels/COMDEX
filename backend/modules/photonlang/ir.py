from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, runtime_checkable, Optional, Dict, Any, Sequence


@dataclass(frozen=True)
class SourceSpan:
    path: str
    start_line: int
    start_col: int
    end_line: int
    end_col: int


@dataclass
class SourceMap:
    strategy: str = "identity-lines"
    line_offset: int = 0
    meta: Dict[str, Any] | None = None


@dataclass
class TransformOptions:
    strict: bool = False
    generate_sourcemap: bool = True
    normalize_roundtrip: bool = True


@dataclass
class TransformResult:
    text: str
    sourcemap: Optional[SourceMap] = None
    stats: Dict[str, Any] | None = None


@runtime_checkable
class Adapter(Protocol):
    """Common interface all language adapters should implement."""
    def expand(self, src: str, *, options: TransformOptions | None = None) -> TransformResult: ...
    def compress(self, src: str, *, options: TransformOptions | None = None) -> TransformResult: ...