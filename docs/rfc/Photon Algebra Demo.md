@SuperFuels ➜ /workspaces/COMDEX (main) $ PYTHONPATH=. python backend/photon_algebra/tests/demo_photon_algebra.py
=== COMDEX Photon Algebra Demo ===

1. Photon-only duality law: a ⊕ ¬a → ⊤

Input: {'op': '⊕', 'states': ['a', {'op': '¬', 'state': 'a'}]}
Normalized: {
  "op": "⊤"
}

2. Complex photon expression collapse

Input: {'op': '⊕', 'states': [{'op': '⊗', 'states': ['a', {'op': '¬', 'state': 'a'}]}, {'op': '⊖', 'states': ['b', 'b']}, {'op': '∅'}]}
Normalized: {
  "op": "⊥"
}

3. Canonical uniqueness across forms

Variant 1: {'op': '⊕', 'states': [{'op': '⊕', 'states': ['a', 'b']}, 'a']}
 → Normalized: {"op": "⊕", "states": ["a", "b"]}
Variant 2: {'op': '⊕', 'states': ['a', {'op': '⊕', 'states': ['b', 'a']}]}
 → Normalized: {"op": "⊕", "states": ["a", "b"]}
Variant 3: {'op': '⊕', 'states': ['b', 'a', 'a']}
 → Normalized: {"op": "⊕", "states": ["a", "b"]}

4. Unique photon operator ★ expansion

Input: {'op': '★', 'state': {'op': '↔', 'states': ['a', 'b']}}
Normalized: {
  "op": "⊕",
  "states": [
    {
      "op": "★",
      "state": "a"
    },
    {
      "op": "★",
      "state": "b"
    }
  ]
}

5. Cache + diagnostics after demo

Cache stats: {'hits': 10, 'misses': 21}
Diag counts: {'rewrites': 0, 'absorptions': 0, 'idempotence': 2, 'distributions': 0}











----------------------

Test Demo

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from backend.photon_algebra.rewriter import normalize, get_cache_stats, DIAG

print("=== COMDEX Photon Algebra Demo ===\n")

# Reset diagnostics before demo
DIAG.reset()

# ----------------------------------------------------------------------
print("1. Photon-only duality law: a ⊕ ¬a → ⊤\n")

expr1 = {"op":"⊕","states":["a", {"op":"¬","state":"a"}]}
print("Input:", expr1)
out1 = normalize(expr1)
print("Normalized:", json.dumps(out1, ensure_ascii=False, indent=2))
print()

# ----------------------------------------------------------------------
print("2. Complex photon expression collapse\n")

expr2 = {
    "op":"⊕","states":[
        {"op":"⊗","states":["a",{"op":"¬","state":"a"}]},
        {"op":"⊖","states":["b","b"]},
        {"op":"∅"}
    ]
}
print("Input:", expr2)
out2 = normalize(expr2)
print("Normalized:", json.dumps(out2, ensure_ascii=False, indent=2))
print()

# ----------------------------------------------------------------------
print("3. Canonical uniqueness across forms\n")

variants = [
    {"op":"⊕","states":[{"op":"⊕","states":["a","b"]},"a"]},
    {"op":"⊕","states":["a",{"op":"⊕","states":["b","a"]}]},
    {"op":"⊕","states":["b","a","a"]},
]

for i, v in enumerate(variants, 1):
    print(f"Variant {i}:", v)
    out = normalize(v)
    print(" → Normalized:", json.dumps(out, ensure_ascii=False))
print()

# ----------------------------------------------------------------------
print("4. Unique photon operator ★ expansion\n")

expr4 = {"op":"★","state":{"op":"↔","states":["a","b"]}}
print("Input:", expr4)
out4 = normalize(expr4)
print("Normalized:", json.dumps(out4, ensure_ascii=False, indent=2))
print()

# ----------------------------------------------------------------------
print("5. Cache + diagnostics after demo\n")
print("Cache stats:", get_cache_stats())
print("Diag counts:", DIAG.to_dict())