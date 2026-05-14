# backend/utils/code_sanitize.py
import io
import unicodedata
import tokenize

# characters that NFKC doesn't fully fix or that we want explicit control over
_TRANSLATION = {
    "...": "...",
    """: '"', """: '"', "'": "'", "'": "'",
    "-": "-", "-": "-", "-": "-", "-": "-",
    "*": "*", "/": "/",
    "*": "*", "*": "*",
    ",": ",", ";": ";",
    "(": "(", ")": ")",
    "[": "[", "]": "]",
    "%": "%", "+": "+", "=": "=", "/": "/",
    "<": "<", ">": ">",
    "!=": "!=", "<=": "<=", ">=": ">=",
    "->": "->", "<-": "<-",
    "->": "->", "<-": "<-",
    # add more if you encounter them
}

def _nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s)

def _translate(s: str) -> str:
    # apply the table above (multi-char replacements allowed)
    out = []
    for ch in s:
        out.append(_TRANSLATION.get(ch, ch))
    return "".join(out)

def sanitize_python_code_ascii(text: str) -> str:
    """
    Make Python source safe ASCII-punct wise.
    Strategy:
      1) NFKC normalize (fixes full-width forms like : -> :)
      2) Apply explicit translation table
      3) Try tokenizing; if tokenization fails, return step (2) result (safe mode)
    We *intentionally* do not attempt to preserve strings/comments separately,
    because we care about buildability; if you need string preservation, add a
    smarter pass later.
    """
    s = _translate(_nfkc(text))

    # Try tokenization just to ensure we didn't break things; if it fails, keep s.
    try:
        _ = list(tokenize.generate_tokens(io.StringIO(s).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return s
    return s