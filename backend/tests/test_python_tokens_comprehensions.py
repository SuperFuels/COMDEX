import ast
from backend.modules.photonlang.adapters.python_tokens import compress_text_py, expand_text_py

SRC = r'''
def h(xs):
    return {
        "list": [x*x for x in xs if x % 2 == 0],
        "set":  {x+1 for x in xs if x>3},
        "dict": {k: v for k, v in enumerate(xs) if k<10},
        "gen":  sum((x for x in xs if x)),
    }
'''

def test_comprehensions_roundtrip():
    comp = compress_text_py(SRC)
    back = expand_text_py(comp)
    assert ast.dump(ast.parse(SRC)) == ast.dump(ast.parse(back))
    assert compile(SRC, "<src>", "exec").co_code == compile(back, "<back>", "exec").co_code