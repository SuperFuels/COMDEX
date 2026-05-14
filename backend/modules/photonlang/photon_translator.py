# 📁 backend/modules/photonlang/photon_translator.py
"""
Photon Translator Core
────────────────────────────────────────────
Maps textual Photon/Python code into glyph-plane representations
using the canonical reserved manifest + language-specific token maps
+ enriched lexicon capsules.

Provides (used by API layer):

  * translate_photon_line(line:str)      -> glyph-string   (legacy)
  * translate_python_block(src:str)      -> glyph-string   (lossless-ish)
"""

import json
import re
import io
import os
import tokenize
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# ─── Paths ────────────────────────────────────────────────────────────────

HERE = Path(__file__).resolve().parent

MANIFEST_PATH = HERE / "photon_reserved_map.json"
PY_TOKEN_MAP_PATH = HERE / "python_token_map.json"

# Default lexicon path (can be overridden via env / API)
DEFAULT_LEXICON_ROOT = (
    HERE.parents[2] / "data" / "knowledge" / "Lexicon_enriched"
    if len(HERE.parents) >= 3
    else None
)

# Limit how many lexicon files we scan on load (for perf)
MAX_LEX_FILES = int(os.getenv("PHOTON_LEXICON_MAX_FILES", "50000"))

print(
    "[LexiconIndex] ROOT =",
    DEFAULT_LEXICON_ROOT,
    "exists?",
    bool(DEFAULT_LEXICON_ROOT and DEFAULT_LEXICON_ROOT.exists()),
)

# ─── Load Reserved Manifest ───────────────────────────────────────────────
try:
    RESERVED = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
except Exception as e:
    RESERVED = {"ops": {}, "keywords": {}, "glyphs": [], "domains": []}
    print(f"[PhotonTranslator] ⚠️ Failed to load manifest: {e}")

ALL_OPS = {op for domain_ops in RESERVED.get("ops", {}).values() for op in domain_ops}
ALL_KW = {kw for domain_kws in RESERVED.get("keywords", {}).values() for kw in domain_kws}

# ─── Load Python token map ────────────────────────────────────────────────
try:
    PY_TOKEN_MAP = json.loads(PY_TOKEN_MAP_PATH.read_text(encoding="utf-8"))
except Exception as e:
    PY_TOKEN_MAP = {"keywords": {}, "operators": {}, "punct": {}}
    print(f"[PhotonTranslator] ⚠️ Failed to load python_token_map.json: {e}")

PY_KW_MAP: Dict[str, str] = PY_TOKEN_MAP.get("keywords", {}) or {}
PY_OP_MAP: Dict[str, str] = PY_TOKEN_MAP.get("operators", {}) or {}

# ─── Lexicon index (wiki capsules) ────────────────────────────────────────


class LexiconIndex:
    """
    Very simple lemma → glyph.symbol index.

    It walks Lexicon_enriched/*.enriched.phn once, looking for:

        lemma: able
        ...
        glyph:
          symbol: ◇✫✮

    and stores { "able": "◇✫✮" }.
    """

    def __init__(self, root: Optional[Path]):
        self.root = root
        self._map: Dict[str, str] = {}
        self._loaded = False

    def _extract_lemma_symbol(self, path: Path) -> Tuple[Optional[str], Optional[str]]:
        """
        Cheap parser for the capsule format.

        We just look for:
          lemma: <word>
          ...
          symbol: <glyph>
        anywhere in the file.
        """
        text = path.read_text(encoding="utf-8", errors="ignore")
        lemma: Optional[str] = None
        symbol: Optional[str] = None

        for line in text.splitlines():
            s = line.strip()

            if s.startswith("lemma:") and lemma is None:
                # e.g. "lemma: able"
                lemma = s.split(":", 1)[1].strip().strip("'\"")

            # inside the glyph block we’ll see "symbol: ◇✫✮"
            if s.startswith("symbol:") and "glyph" not in s and symbol is None:
                symbol = s.split("symbol:", 1)[1].strip().strip("'\"")

            if lemma and symbol:
                break

        return lemma, symbol

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True

        root = self.root
        if not root or not root.exists():
            print("[LexiconIndex] ⚠️ Lexicon root missing; word→glyph disabled.", root)
            return

        count = 0
        for i, path in enumerate(root.glob("*.enriched.phn")):
            if i >= MAX_LEX_FILES:
                break
            try:
                lemma, symbol = self._extract_lemma_symbol(path)
                if lemma and symbol:
                    self._map[lemma.lower()] = symbol
                    count += 1
            except Exception as e:
                print(f"[LexiconIndex] skip {path.name}: {e}")
                continue

        print(f"[LexiconIndex] Loaded {count} lemma→glyph mappings from {root}")

    def lookup(self, word: str) -> Optional[str]:
        if not self._loaded:
            self._load()
        return self._map.get(word.lower())


# ─── Shared singleton Lexicon index ───────────────────────────────────────

LEXICON_INDEX = LexiconIndex(DEFAULT_LEXICON_ROOT)

# ─── Core Translator ──────────────────────────────────────────────────────


class PhotonTranslator:
    """
    language="photon"  → legacy line-by-line Photon translator
    language="python"  → token-aware, lossless-ish Python → glyph
    """

    def __init__(
        self,
        language: str = "photon",
        enable_lexicon: bool = True,
        lexicon_root: Optional[Path] = None,
    ):
        self.language = language
        self.reserved_ops = ALL_OPS
        self.reserved_kw = ALL_KW
        self.glyph_map = self._build_glyph_map()
        self.enable_lexicon = enable_lexicon

        # reuse the shared lexicon index unless a custom root is explicitly given
        if lexicon_root is not None:
            self.lexicon = LexiconIndex(lexicon_root)
        else:
            self.lexicon = LEXICON_INDEX

    # ─── Small static glyph map for Photon keywords ───────────────────────
    def _build_glyph_map(self) -> Dict[str, str]:
        """Static demo glyph-map (extendable via wiki lexicon later)."""
        return {
            "container_id": "💡",
            "wave": "🌊",
            "resonance": "🌀",
            "memory": "🧠",
            "photon": "⚛",
            "quantum": "✦",
            "field": "🜁",
            "nav": "🧭",
        }

    # ─── Public translation entrypoints ───────────────────────────────────

    def translate_line(self, line: str) -> str:
        """
        Backwards-compatible entrypoint.

        For language="photon" it uses the original inline replacement.
        For language="python" it treats the line as a small Python block.
        """
        if self.language == "python":
            return self.translate_python_block(line)
        return self._translate_photon_line(line)

    def translate_python_block(self, src: str) -> str:
        """
        Lossless-ish Python → glyph translator.

        Uses tokenize.generate_tokens + untokenize to preserve layout,
        and only changes the token *strings*.

        If the source is not valid Python (e.g. TSX/JSX), we catch the
        tokenize error and fall back to returning the original text so
        the API never 500s.
        """
        buf = io.StringIO(src)
        out_tokens: List[tokenize.TokenInfo] = []

        try:
            for tok in tokenize.generate_tokens(buf.readline):
                ttype, tstring, start, end, line = tok
                new_str = tstring

                if ttype == tokenize.NAME:
                    # Python keyword?
                    mapped = PY_KW_MAP.get(tstring)
                    if mapped:
                        new_str = mapped

                elif ttype == tokenize.OP:
                    mapped = PY_OP_MAP.get(tstring)
                    if mapped:
                        new_str = mapped

                elif ttype == tokenize.STRING:
                    new_str = self._translate_string_token(tstring)

                elif ttype == tokenize.COMMENT:
                    new_str = self._translate_comment_token(tstring)

                # Everything else (indentation, whitespace, numbers, etc.) stays verbatim
                out_tokens.append(
                    tokenize.TokenInfo(ttype, new_str, start, end, line)
                )

            return tokenize.untokenize(out_tokens)

        except tokenize.TokenError as e:
            print(f"[PhotonTranslator] ⚠️ tokenize error, falling back to raw text: {e}")
            # For non-Python blobs (TSX, JSON, etc.), just give the raw text back
            return src

        except Exception as e:
            print(f"[PhotonTranslator] ⚠️ python translation failed: {e}")
            return src

    # ─── Legacy Photon translator (line-based) ─────────────────────────────
    def _translate_photon_line(self, line: str) -> str:
        """Original behavior kept for backwards compatibility."""
        if not line.strip():
            return ""

        out = line

        # Replace keywords -> [kw]
        for kw in sorted(self.reserved_kw, key=len, reverse=True):
            out = re.sub(rf"\b{re.escape(kw)}\b", f"[{kw}]", out)

        # Replace glyph map entries
        for word, glyph in self.glyph_map.items():
            out = re.sub(rf"\b{re.escape(word)}\b", glyph, out)

        # Highlight operators
        for op in self.reserved_ops:
            out = out.replace(op, f" {op} ")

        return out.strip()

    # ─── Plain text → word glyphs / Photon glyphs ─────────────────────────
    def _translate_plain_text(self, text: str) -> str:
        """
        Run over *natural language* blobs (comments, string bodies).

        Order:
          1) photon glyph_map words (wave, resonance, memory, …)
          2) lexicon-enriched wiki lemmas (able, quantum, …)
          3) otherwise keep as-is
        """

        def repl(m: re.Match) -> str:
            word = m.group(0)
            # Photon reserved words first (container_id, wave, …)
            g = self.glyph_map.get(word)
            if g:
                return g

            if self.enable_lexicon:
                g2 = self.lexicon.lookup(word)
                if g2:
                    return g2

            return word

        # word-ish: includes identifiers in strings, but not punctuation / escapes
        return re.sub(r"[A-Za-z][A-Za-z0-9_]*", repl, text)

    # ─── String/comment helpers ───────────────────────────────────────────
    _STRING_RE = re.compile(
        r"(?P<prefix>[rubfRUBF]*)(?P<quote>'''|\"\"\"|'|\")(?P<body>.*)(?P=quote)$",
        re.S,
    )

    def _translate_string_token(self, token: str) -> str:
        """
        Preserve prefix & quote style, only rewrite *body* words.
        """
        m = self._STRING_RE.match(token)
        if not m:
            return token

        prefix = m.group("prefix")
        quote = m.group("quote")
        body = m.group("body")

        new_body = self._translate_plain_text(body)
        return f"{prefix}{quote}{new_body}{quote}"

    def _translate_comment_token(self, token: str) -> str:
        """
        "# Photon test script for SCI IDE" → "#" + glyphified text.
        """
        if not token.startswith("#"):
            return token
        body = token[1:]
        new_body = self._translate_plain_text(body)
        return "#" + new_body

    # ─── Compile file (kept for Photon; can be reused for Python) ─────────
    def compile_file(self, path: str) -> Dict[str, Any]:
        """
        Compile source file into a symbolic capsule (AST placeholder).

        For language="photon" this keeps the legacy line-by-line behavior.
        For language="python" it uses translate_python_block on the whole file.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(path)

        src = p.read_text(encoding="utf-8")

        if self.language == "python":
            translated = self.translate_python_block(src)
        else:
            lines = src.splitlines()
            translated_lines = [self._translate_photon_line(l) for l in lines]
            translated = "\n".join(translated_lines)

        return {
            "source": str(p),
            "translated": translated,
            "glyph_count": translated.count("💡")
            + translated.count("🌊")
            + translated.count("🧠"),
            "domains": RESERVED.get("domains", []),
        }


# ─── Exported helpers used by the API layer ───────────────────────────────

# shared instances
_PHOTON_TRANSLATOR = PhotonTranslator(language="photon")
_PYTHON_TRANSLATOR = PhotonTranslator(language="python")


def translate_photon_line(line: str) -> str:
    """
    Legacy helper: PhotonTranslator(language="photon").
    """
    return _PHOTON_TRANSLATOR.translate_line(line)


def translate_python(src: str) -> str:
    """
    New helper for the DevTools Photon editor:

      * understands Python tokens
      * maps def/return/async/await/etc. via python_token_map.json
      * glyphifies comments + strings via Lexicon_enriched capsules
    """
    return _PYTHON_TRANSLATOR.translate_python_block(src)


if __name__ == "__main__":
    pt = PhotonTranslator(language="python")
    sample = 'import quantum\ncontainer_id = wave ⊕ resonance\n# able sailor\nprint("hello able world")'
    print("Original:\n", sample)
    print("Translated:\n", pt.translate_python_block(sample))