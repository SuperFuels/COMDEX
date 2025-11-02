import pytest
from backend.modules.photonlang_js.adapters.js_tokens import compress_text_js, expand_text_js

def test_roundtrip_ops_basic():
    js = "if (a != b && c == d) { f(a,b); }"
    comp = compress_text_js(js).text
    assert "≠≟" in comp and "∧̄" in comp and "≟≟" in comp

    back = expand_text_js(comp).text
    assert back == js