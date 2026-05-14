# backend/modules/photonlang/translator.py
from __future__ import annotations

# Glyphs that behave like function calls: ⊕(a,b), μ(x), ↔(a,b), ⟲(f,n), π(seq,n)
GLYPH_CALLS = {"⊕", "μ", "↔", "⟲", "π"}

def expand_symatics_ops(src: str) -> str:
    """
    Rewrite call-like glyphs outside strings/comments to __OPS__["<glyph>"](...).
    Also injects: `from backend.symatics.operators import OPS as __RAW_OPS` and
    resolves each operator to a callable (__OPS__) so call sites fail cleanly
    (with a good traceback) if an operator isn't directly callable.
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

    # Inject runtime import + resolver once if file doesn't already reference __OPS__
    if "__OPS__" not in src:
        prolog = (
            'from backend.symatics.operators import OPS as __RAW_OPS\n'
            'def __resolve_op(name, v):\n'
            '    if callable(v):\n'
            '        return v\n'
            '    # try common method/attr names on objects\n'
            '    for nm in (\n'
            '        "__call__", "apply", "call", "invoke", "run",\n'
            '        "evaluate", "eval", "exec", "execute",\n'
            '        "op", "fn", "func", "function", "impl", "implementation",\n'
            '    ):\n'
            '        attr = getattr(v, nm, None)\n'
            '        if callable(attr):\n'
            '            return (lambda attr=attr: (lambda *a, **k: attr(*a, **k)))()\n'
            '    # mapping-like containers\n'
            '    if isinstance(v, dict):\n'
            '        for nm in ("call", "apply", "fn", "func", "impl", "implementation"):\n'
            '            attr = v.get(nm)\n'
            '            if callable(attr):\n'
            '                return attr\n'
            '    # fallback: keep import working; raise at call site for clean tracebacks\n'
            '    def __missing(*a, **k):\n'
            '        raise TypeError(\n'
            '            f\'Photon operator "{name}" isn\\\'t callable (no apply/call/invoke/etc). Type={type(v).__name__}\'\n'
            '        )\n'
            '    return __missing\n'
            '__OPS__ = {k: __resolve_op(k, v) for k, v in __RAW_OPS.items()}\n'
        )
        return prolog + body

    return body

# Back-compat: some older code may call translator.expand(...)
def expand(src: str, module_name: str = "", source_path: str = "") -> str:  # noqa: ARG001
    return expand_symatics_ops(src)