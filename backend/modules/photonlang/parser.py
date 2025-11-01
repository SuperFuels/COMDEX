# backend/modules/photonlang/parser.py
from __future__ import annotations
import re, json
from pathlib import Path
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

# === Load operator runes from photon_reserved_map.json ===
_PH_MAP = Path(__file__).parent / "photon_reserved_map.json"
def _op_class() -> str:
    try:
        data = json.loads(_PH_MAP.read_text(encoding="utf-8"))
        ops = data.get("ops", {})
        runes = set()
        for arr in ops.values():
            for token in arr:
                for ch in token:  # split "μπ" into μ, π
                    runes.add(ch)
        # IMPORTANT: do NOT include DEFAULT "✦" as an operator.
        runes.discard("✦")
        # Escape for regex character class
        esc = "".join(re.escape(c) for c in sorted(runes))
        return f"[{esc}]+"
    except Exception:
        # Fallback - keep small, safe set
        return r"[⊕↔⟲μπ->∇⊗->⧖≈]+"

GLYPHSEQ_RE = _op_class()

# ============================================================
# TOKENIZER
# ============================================================
TOK_SPEC = [
    ("NEWLINE",   r"\r?\n+"),
    ("WS",        r"[ \t]+"),
    ("COMMENT",   r"\#.*"),

    # Keywords
    ("KW_IMPORT",   r"\bimport\b"),
    ("KW_FROM",     r"\bfrom\b"),
    ("KW_WORMHOLE", r"\bwormhole\b"),
    ("KW_SEND",     r"\bsend\b"),
    ("KW_THROUGH",  r"\bthrough\b"),
    ("KW_SAVE",     r"\bsave\b"),
    ("KW_AS",       r"\bas\b"),

    # Symbols
    ("LPAREN", r"\("),
    ("RPAREN", r"\)"),
    ("LBRACE", r"\{"),
    ("RBRACE", r"\}"),
    ("COMMA",  r","),
    ("DOT",    r"\."),
    ("EQ",     r"="),
    ("COLON",  r":"),

    # Photon symbolic operators - built from JSON
    ("GLYPHSEQ", GLYPHSEQ_RE),

    # Literals
    ("NUMBER", r"[0-9]+(?:\.[0-9]+)?"),
    ("STRING", r"\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'"),

    # Identifiers & URIs
    ("URI",   r"[A-Za-z_][A-Za-z0-9+.\-]*://[A-Za-z0-9_\-./]+"),
    ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
]

TOK_RE = re.compile("|".join(f"(?P<{n}>{p})" for n, p in TOK_SPEC))


@dataclass
class Token:
    typ: str
    val: str
    pos: int


def tokenize(src: str) -> List[Token]:
    """Convert PhotonLang source into a token sequence."""
    toks: List[Token] = []
    for m in TOK_RE.finditer(src):
        typ = m.lastgroup or ""
        val = m.group()
        if typ in ("WS", "COMMENT", "NEWLINE"):
            continue
        toks.append(Token(typ, val, m.start()))
    toks.append(Token("EOF", "", len(src)))
    return toks


# ============================================================
# AST NODES
# ============================================================

@dataclass
class Node: pass

@dataclass
class Program(Node): stmts: List[Node]
@dataclass
class ImportStmt(Node): names: List[str]
@dataclass
class FromImport(Node): module: str; version: Optional[str]; names: List[str]
@dataclass
class WormholeImport(Node): uri: str; name: str
@dataclass
class GlyphInit(Node): seq: str
@dataclass
class GlyphStmt(Node): seq: str; params: dict   # ⧖ {freq=1.1} etc
@dataclass
class Assign(Node): name: str; expr: Node
@dataclass
class Call(Node): func: Node; args: List[Tuple[Optional[str], Node]]
@dataclass
class Attr(Node): obj: Node; name: str
@dataclass
class Name(Node): id: str
@dataclass
class Literal(Node): value: Any
@dataclass
class SendThrough(Node): obj: Node; uri: str
@dataclass
class SaveAs(Node): target: Node


# ============================================================
# PARSER
# ============================================================

class Parser:
    def __init__(self, toks: List[Token]):
        self.toks = toks
        self.i = 0

    def cur(self) -> Token:
        return self.toks[self.i]

    def accept(self, *types) -> Optional[Token]:
        if self.cur().typ in types:
            t = self.cur()
            self.i += 1
            return t
        return None

    def expect(self, t: str) -> Token:
        tok = self.accept(t)
        if not tok:
            raise SyntaxError(
                f"Expected {t} at {self.cur().pos}, got {self.cur().typ}"
            )
        return tok

    # --------------------------------------------------------
    # Entry: program
    # --------------------------------------------------------
    def parse(self) -> Program:
        stmts: List[Node] = []
        while self.cur().typ != "EOF":
            if self.cur().typ in ("WS", "COMMENT", "NEWLINE"):
                self.i += 1
                continue
            stmts.append(self.stmt())
        return Program(stmts)

    # --------------------------------------------------------
    # Statement-level grammar
    # --------------------------------------------------------
    def stmt(self) -> Node:
        # import X[, Y]
        if self.accept("KW_IMPORT"):
            names = [self.expect("IDENT").val]
            while self.accept("COMMA"):
                names.append(self.expect("IDENT").val)
            return ImportStmt(names)

        # from ...
        if self.accept("KW_FROM"):
            # wormhole form
            if self.cur().typ in ("LPAREN", "URI") and (
                self.cur().typ == "LPAREN" or self.cur().val.startswith("wormhole:")
            ):
                # "(wormhole: uri)" form
                if self.accept("LPAREN"):
                    if self.cur().typ in ("KW_WORMHOLE", "IDENT"):
                        self.i += 1
                    if self.cur().typ == "COLON": self.i += 1
                    if self.cur().typ not in ("URI", "STRING"):
                        raise SyntaxError(
                            f"Expected URI after wormhole:, got {self.cur().typ}"
                        )
                    uri = self.cur().val
                    self.i += 1
                    self.expect("RPAREN")
                else:
                    # "wormhole:uri" form
                    val = self.cur().val
                    if not val.startswith("wormhole:"):
                        raise SyntaxError(f"Invalid wormhole syntax @ {self.cur().pos}")
                    uri = val.split("wormhole:", 1)[1]
                    self.i += 1

                self.expect("KW_IMPORT")
                name = self.expect("IDENT").val
                return WormholeImport(uri, name)

            # normal from-import
            module = self.dotted()
            ver = None
            if self.cur().typ == "NUMBER":
                ver = self.expect("NUMBER").val
            self.expect("KW_IMPORT")
            names = [self.expect("IDENT").val]
            while self.accept("COMMA"):
                names.append(self.expect("IDENT").val)
            return FromImport(module, ver, names)

        # glyph init (no params)
        if self.cur().typ == "GLYPHSEQ":
            seq = self.expect("GLYPHSEQ").val
            # check for ⧖ {freq=...}
            if self.accept("LBRACE"):
                params = {}
                while not self.accept("RBRACE"):
                    name = self.expect("IDENT").val
                    self.expect("EQ")
                    val = float(self.expect("NUMBER").val)
                    params[name] = val
                    self.accept("COMMA")
                return GlyphStmt(seq, params)
            return GlyphInit(seq)

        # send ... through wormhole
        if self.cur().typ == "KW_SEND":
            self.expect("KW_SEND")
            obj = self.expr()
            self.expect("KW_THROUGH")
            self.accept("KW_WORMHOLE")
            uri = self.expect("STRING").val.strip("\"'")
            return SendThrough(obj, uri)

        # save as
        if self.cur().typ == "KW_SAVE":
            self.expect("KW_SAVE")
            self.expect("KW_AS")
            if self.cur().typ == "STRING":
                return SaveAs(Literal(self.expect("STRING").val.strip("\"'")))
            return SaveAs(Name(self.expect("IDENT").val))

        # assignment or expr
        if self.cur().typ == "IDENT":
            t = self.cur()
            self.i += 1
            if self.accept("EQ"):
                expr = self.expr()
                return Assign(t.val, expr)
            self.i -= 1
            return self.expr()

        return self.expr()
    # --------------------------------------------------------
    # Expression handling
    # --------------------------------------------------------
    def dotted(self) -> str:
        parts = []

        # allow relative import: from .foo import X
        while self.accept("DOT"):
            parts.append("")  # mark relative depth

        if self.cur().typ != "IDENT":
            raise SyntaxError(
                f"Expected IDENT in dotted path at {self.cur().pos}, got {self.cur().typ}"
            )

        parts.append(self.expect("IDENT").val)

        while self.accept("DOT"):
            parts.append(self.expect("IDENT").val)

        return ".".join(parts)

    # --------------------------------------------------------
    # Expression / trailers: foo, foo(), foo.bar(), foo().x
    # --------------------------------------------------------
    def expr(self) -> Node:
        node = self.primary()

        while True:
            # attribute or method call:  x.y / x.y()
            if self.accept("DOT"):
                name = self.expect("IDENT").val
                # x.y(...)
                if self.accept("LPAREN"):
                    args = self.arg_list_opt()
                    node = Call(Attr(node, name), args)
                else:
                    # x.y
                    node = Attr(node, name)
                continue

            # function call:  x(...)
            if self.accept("LPAREN"):
                args = self.arg_list_opt()
                node = Call(node, args)
                continue

            break

        return node

    # --------------------------------------------------------
    # Primary expressions
    # --------------------------------------------------------
    def primary(self) -> Node:
        t = self.cur()

        # identifier reference
        if t.typ == "IDENT":
            self.i += 1
            return Name(t.val)

        # quoted literal
        if t.typ == "STRING":
            self.i += 1
            val = t.val.strip("\"'")
            return Literal(val)

        # numeric literal
        if t.typ == "NUMBER":
            self.i += 1
            if "." in t.val:
                return Literal(float(t.val))
            return Literal(int(t.val))

        raise SyntaxError(f"Unexpected token {t.typ} at {t.pos}")

    # --------------------------------------------------------
    # Argument list parsing: (a, b=3, x(4))
    # --------------------------------------------------------
    def arg_list_opt(self) -> List[Tuple[Optional[str], Node]]:
        args: List[Tuple[Optional[str], Node]] = []

        # Empty call "()"
        if self.accept("RPAREN"):
            return args

        while True:
            # key=value vs bare expr
            if self.cur().typ == "IDENT":
                name_tok = self.cur()
                self.i += 1

                if self.accept("EQ"):
                    val = self.expr()
                    args.append((name_tok.val, val))
                else:
                    # not assignment; revert & parse expr
                    self.i -= 1
                    args.append((None, self.expr()))
            else:
                args.append((None, self.expr()))

            # comma = more args
            if self.accept("COMMA"):
                continue

            # close call
            self.expect("RPAREN")
            break

        return args

# ============================================================
# Helper Entry
# ============================================================

def parse_source(src: str) -> Program:
    """
    Public entrypoint for Parser.
    Clean wrapper for interpreter and test harness.
    """
    return Parser(tokenize(src)).parse()