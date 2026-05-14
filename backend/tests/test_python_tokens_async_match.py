# backend/tests/test_python_tokens_async_match.py
import ast
from backend.modules.photonlang.adapters.python_tokens import compress_text_py, expand_text_py

SRC = r'''
import math, sys
async def af(x: int) -> int:
    await coro()
    match x:
        case 0: return 0
        case y if y > 0: return y
        case _: return -1

@dec
def f(a: int, b: str="t") -> tuple[int, str]:
    z = (a := (len(b) if b else 3))
    return (z, f"{b!r}:{a:04d}")
'''

def test_async_match_roundtrip():
    comp = compress_text_py(SRC)
    back = expand_text_py(comp)
    assert ast.dump(ast.parse(SRC)) == ast.dump(ast.parse(back))
    assert compile(SRC, "<src>", "exec").co_code == compile(back, "<back>", "exec").co_code