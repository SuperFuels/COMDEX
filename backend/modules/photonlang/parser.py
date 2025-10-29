from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

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
    ("COMMA",  r","),
    ("DOT",    r"\."),
    ("EQ",     r"="),
    ("COLON",  r":"),

    # Photon symbolic operators
    ("GLYPHSEQ", r"[⊕↔⟲μπ⇒∇⊗✦→⧖≈]+"),

    # Literals
    ("NUMBER", r"[0-9]+(?:\.[0-9]+)?"),
    ("STRING", r"\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'"),

    # Identifiers and URIs (⚙️ corrected)
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
            raise SyntaxError(f"Expected {t} at position {self.cur().pos}, got {self.cur().typ}")
        return tok

    # --------------------------------------------------------
    # Parse Entry
    # --------------------------------------------------------
    def parse(self) -> Program:
        stmts: List[Node] = []
        while self.cur().typ != "EOF":
            # Skip comments, whitespace, stray glyphs
            if self.cur().typ in ("WS", "COMMENT", "NEWLINE"):
                self.i += 1
                continue
            stmts.append(self.stmt())
        return Program(stmts)

    # --------------------------------------------------------
    # Statement-level parsing
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
            # detect wormhole imports — either '(' or inline 'wormhole:' URI
            if self.cur().typ in ("LPAREN", "URI") and (
                self.cur().typ == "LPAREN" or self.cur().val.startswith("wormhole:")
            ):
                # Handle wrapped wormhole form: from (wormhole: quantum://...) import X
                if self.accept("LPAREN"):
                    if self.cur().typ in ("KW_WORMHOLE", "IDENT"):
                        self.i += 1  # consume 'wormhole'
                    if self.cur().typ == "COLON":
                        self.i += 1
                    if self.cur().typ not in ("URI", "STRING"):
                        raise SyntaxError(f"Expected URI after wormhole:, got {self.cur().typ}")
                    uri = self.cur().val
                    self.i += 1
                    self.expect("RPAREN")
                else:
                    # Inline style: from wormhole: quantum://... import X
                    val = self.cur().val
                    if val.startswith("wormhole:"):
                        uri = val.split("wormhole:", 1)[1]
                        self.i += 1
                    else:
                        raise SyntaxError(f"Invalid inline wormhole syntax at {self.cur().pos}")

                self.expect("KW_IMPORT")
                name = self.expect("IDENT").val
                return WormholeImport(uri, name)

            # fallback to normal from-import
            module = self.dotted()
            ver = None
            if self.cur().typ == "NUMBER":
                ver = self.expect("NUMBER").val
            self.expect("KW_IMPORT")
            names = [self.expect("IDENT").val]
            while self.accept("COMMA"):
                names.append(self.expect("IDENT").val)
            return FromImport(module, ver, names)

        # symbolic glyph init line
        if self.cur().typ == "GLYPHSEQ":
            seq = self.expect("GLYPHSEQ").val
            return GlyphInit(seq)

        # send ... through wormhole "..."
        if self.cur().typ == "KW_SEND":
            self.expect("KW_SEND")
            obj = self.expr()
            self.expect("KW_THROUGH")
            self.accept("KW_WORMHOLE")
            uri = self.expect("STRING").val.strip("\"'")
            return SendThrough(obj, uri)

        # save as "..."
        if self.cur().typ == "KW_SAVE":
            self.expect("KW_SAVE")
            self.expect("KW_AS")
            if self.cur().typ == "STRING":
                return SaveAs(Literal(self.expect("STRING").val.strip("\"'")))
            return SaveAs(Name(self.expect("IDENT").val))

        # assignment or expression
        if self.cur().typ == "IDENT":
            t = self.cur()
            self.i += 1
            if self.accept("EQ"):
                expr = self.expr()
                return Assign(t.val, expr)
            else:
                self.i -= 1
                return self.expr()

        return self.expr()

    # --------------------------------------------------------
    # Expression handling
    # --------------------------------------------------------
    def dotted(self) -> str:
        parts = []
        # Allow leading dot for relative imports (e.g. `from .module import X`)
        while self.accept("DOT"):
            parts.append("")  # placeholder for each leading dot
        # Expect first identifier
        if self.cur().typ != "IDENT":
            raise SyntaxError(f"Expected IDENT at {self.cur().pos}, got {self.cur().typ}")
        parts.append(self.expect("IDENT").val)
        # Accept further `.ident` chains
        while self.accept("DOT"):
            parts.append(self.expect("IDENT").val)
        return ".".join(parts)

    def expr(self) -> Node:
        node = self.primary()
        while True:
            if self.accept("DOT"):
                name = self.expect("IDENT").val
                if self.accept("LPAREN"):
                    args = self.arg_list_opt()
                    node = Call(Attr(node, name), args)
                else:
                    node = Attr(node, name)
                continue
            if self.accept("LPAREN"):
                args = self.arg_list_opt()
                node = Call(node, args)
                continue
            break
        return node

    def primary(self) -> Node:
        t = self.cur()
        if t.typ == "IDENT":
            self.i += 1
            return Name(t.val)
        if t.typ == "STRING":
            self.i += 1
            return Literal(t.val.strip("\"'"))
        if t.typ == "NUMBER":
            self.i += 1
            return Literal(float(t.val) if "." in t.val else int(t.val))
        raise SyntaxError(f"Unexpected token {t.typ} at {t.pos}")

    def arg_list_opt(self) -> List[Tuple[Optional[str], Node]]:
        args: List[Tuple[Optional[str], Node]] = []
        if self.accept("RPAREN"):
            return args
        while True:
            if self.cur().typ == "IDENT":
                name_tok = self.cur()
                self.i += 1
                if self.accept("EQ"):
                    val = self.expr()
                    args.append((name_tok.val, val))
                else:
                    self.i -= 1
                    args.append((None, self.expr()))
            else:
                args.append((None, self.expr()))
            if self.accept("COMMA"):
                continue
            self.expect("RPAREN")
            break
        return args

# ============================================================
# Helper
# ============================================================

def parse_source(src: str) -> Program:
    """Entry point for external modules (e.g., interpreter)."""
    return Parser(tokenize(src)).parse()