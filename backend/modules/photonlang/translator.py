# backend/modules/photonlang/translator.py
from __future__ import annotations

# Glyphs that behave like function calls: ⊕(a,b), μ(x), ↔(a,b), ⟲(f,n), π(seq,n)
GLYPH_CALLS = {"⊕", "μ", "↔", "⟲", "π"}

def expand_symatics_ops(src: str) -> str:
    """
    Rewrite call-like glyphs outside strings/comments to __OPS__["<glyph>"](...).
    Also injects: `from backend.symatics.operators import OPS as __OPS__`
    at the top if __OPS__ isn't already referenced in the file.
    """
    out: list[str] = []
    i = 0
    n = len(src)

    in_quote: str | None = None   # "'" or '"'
    triple = False
    esc = False

    while i < n:
        ch = src[i]

        # ----- inside a string -----
        if in_quote:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif triple:
                if ch == in_quote and src[i:i+3] == in_quote * 3:
                    out.append(src[i+1:i+3])
                    i += 2
                    in_quote = None
                    triple = False
            else:
                if ch == in_quote:
                    in_quote = None
            i += 1
            continue

        # ----- start of string -----
        if ch in ("'", '"'):
            if src[i:i+3] == ch * 3:
                in_quote = ch
                triple = True
                out.append(ch * 3)
                i += 3
            else:
                in_quote = ch
                triple = False
                out.append(ch)
                i += 1
            continue

        # ----- comment -----
        if ch == "#":
            j = src.find("\n", i)
            if j == -1:
                out.append(src[i:])
                break
            out.append(src[i:j+1])
            i = j + 1
            continue

        # ----- glyph call rewrite -----
        if ch in GLYPH_CALLS:
            j = i + 1
            while j < n and src[j].isspace():
                j += 1
            if j < n and src[j] == "(":
                # "⊕   (" -> '__OPS__["⊕"]   ('
                out.append('__OPS__["')
                out.append(ch)
                out.append('"]')
                out.append(src[i+1:j])  # keep original whitespace
                out.append("(")
                i = j + 1
                continue

        # default copy
        out.append(ch)
        i += 1

    body = "".join(out)
    # Inject runtime import once if file doesn't already reference __OPS__
    if "__OPS__" not in src:
        prolog = 'from backend.symatics.operators import OPS as __OPS__\n'
        return prolog + body
    return body

# Back-compat: some older code may call translator.expand(...)
def expand(src: str, module_name: str = "", source_path: str = "") -> str:  # noqa: ARG001
    return expand_symatics_ops(src)