# backend/modules/photon/photon_parser.py
import re

TOKEN_PATTERN = re.compile(r'([⊕↔∇μ⟲])|([\w\-\_]+)')

class PhotonParser:
    """Minimal Photon Language tokenizer and AST generator (v0.1)."""

    def parse(self, src: str):
        tokens = [t for t in re.findall(TOKEN_PATTERN, src) if any(t)]
        ast = []
        for symbol, word in tokens:
            if symbol:
                ast.append({"type": "op", "value": symbol})
            elif word:
                ast.append({"type": "arg", "value": word})
        return ast