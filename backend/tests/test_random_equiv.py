import ast
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from backend.modules.photonlang.adapters.python_tokens import (
    compress_text_py, expand_text_py
)

# simple identifier generator
ident = st.from_regex(r"[A-Za-z_][A-Za-z0-9_]{0,6}", fullmatch=True)
ints = st.integers(min_value=0, max_value=8)

def _prog(a: str, b: str, n: int) -> str:
    return f'''
import math
def f({a}: int, {b}: int = {n}):
    # walrus on RHS must be parenthesized in valid Python
    __z = ({a} := ({b} if {b} else {n}))
    if __z % 2 == 0:
        t = (__z // 2)
    else:
        t = (__z * 3 + 1)
    match t % 3:
        case 0: y = 0
        case 1: y = 1
        case _: y = -1
    comp = [i*i for i in range({n}) if i % 2 == 0]
    return (__z, t, y, comp)
'''

@settings(deadline=None, suppress_health_check=[HealthCheck.filter_too_much])
@given(a=ident, b=ident, n=ints)
def test_random_equiv(a, b, n):
    # ensure parameters are distinct to avoid duplicate-arg SyntaxError
    assume(a != b)

    src = _prog(a, b, n)
    comp = compress_text_py(src)
    back = expand_text_py(comp)

    assert ast.dump(ast.parse(src)) == ast.dump(ast.parse(back))
    assert compile(src, "<src>", "exec").co_code == compile(back, "<back>", "exec").co_code