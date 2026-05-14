# backend/tests/test_code_normalize_regressions.py
import ast
from backend.tests.test_python_corpus import _aggressive_ascii_normalize, sanitize_python_code_ascii

CASES = [
    ("x = 1 e − 9", "x = 1e-9"),
    ("mu = 1 E 6",   "mu = 1e6"),
    ("np . linspace(0 , 1 , 5)", "np.linspace(0, 1, 5)"),
    ("a = 1 . 0", "a = 1.0"),
]

def test_normalizer_regressions():
    for raw, expected_contains in CASES:
        s = sanitize_python_code_ascii(_aggressive_ascii_normalize(raw))
        # must parse and contain the glued token
        ast.parse(s)
        assert expected_contains in s