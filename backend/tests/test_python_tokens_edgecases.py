import ast
import textwrap
from backend.modules.photonlang.adapters.python_tokens import compress_text_py, expand_text_py

CASES = {
    "walrus_and_comp": """
def f(xs):
    if (n := len(xs)) > 2:
        return [y for y in xs if (m := y+1) > 0]
    return 0
""",
    "match_case": """
def g(x):
    match x:
        case {"a": 1}:
            return 1
        case [h, *t]:
            return h
        case _:
            return None
""",
    "type_unions_and_ann": """
from typing import Optional
def h(x: int | str | None) -> Optional[int | str]:
    y: dict[str, list[int | None]] = {}
    return x
""",
    "decorators_and_kwargs": """
def deco(fn): return fn
@deco
def k(a, b=1, *args, **kwargs):
    return f"{a}:{b}:{kwargs.get('k','')}"
""",
    "fstring_safety": r'''
def s():
    inner = "{not_touched}"
    return f"brace {{ stays }} and {inner}"
''',
}

def _norm(s: str) -> str:
    return textwrap.dedent(s).lstrip("\n")

def test_edgecases_roundtrip_ast_and_bytecode():
    for name, src in CASES.items():
        src = _norm(src)
        comp = compress_text_py(src)          # py -> photon-glyphs
        back = expand_text_py(comp)           # photon-glyphs -> py
        assert ast.dump(ast.parse(src)) == ast.dump(ast.parse(back)), name
        assert compile(src, "<src>", "exec").co_code == compile(back, "<back>", "exec").co_code, name