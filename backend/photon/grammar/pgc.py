TOKENS = {
  "⊕": "SUPERPOSE",
  "↔": "ENTANGLE",
  "⟲": "RESONATE",
  "∇": "COLLAPSE",
  "μ": "MEASURE",
  "π": "PROJECT",
  "->": "TRIGGER",
}

def tokenize(src: str):
    return [TOKENS[ch] for ch in src if ch in TOKENS]

def parse(tokens):
    # v0: linear check, v1: LL(1)
    if tokens[-1] not in ("COLLAPSE", "RESONATE"):
        raise SyntaxError("Photon program must end in ∇ or ⟲")
    return tokens