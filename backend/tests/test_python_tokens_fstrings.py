import ast
from backend.modules.photonlang.adapters.python_tokens import compress_text_py, expand_text_py

SRC = r'''
def g(x, y):
    return f"sum={x+y!r} [{x:0>4}] {{literal}} {(lambda z: z*2)(y)}"
'''

def test_fstring_roundtrip():
    comp = compress_text_py(SRC)
    back = expand_text_py(comp)
    assert ast.dump(ast.parse(SRC)) == ast.dump(ast.parse(back))
    assert compile(SRC, "<src>", "exec").co_code == compile(back, "<back>", "exec").co_code