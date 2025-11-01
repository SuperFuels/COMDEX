import ast
from backend.modules.photonlang.adapters.python_tokens import compress_text_py, expand_text_py

CASES = [
    "def f(x:int=1)->int:\n    if x<=2: return x+1\n",
    "class C:\n    def m(self):\n        try:\n            return 1\n        except ValueError as e:\n            pass\n        finally:\n            pass\n",
    "from x import y, z\nfor i in range(3):\n    continue\n",
    "s = 'def if : ( ) should not change'; t=f\"return {1+2}\"\n",
]

def ast_norm(s: str): return ast.dump(ast.parse(s, mode="exec"), include_attributes=False)

def test_roundtrip_ast():
    for src in CASES:
        comp = compress_text_py(src)
        back = expand_text_py(comp)
        assert ast_norm(src) == ast_norm(back)