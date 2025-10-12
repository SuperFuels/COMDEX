# Glyph → Lean operator bindings
# =========================================
# Defines canonical translation between
# Symatics glyph symbols (⊕, μ, ⟲, π, ↔, πₛ)
# and their corresponding Lean namespace functions.

GLYPH_TO_LEAN = {
    "⊕": "Symatics.superpose",
    "⟲": "Symatics.resonate",
    "μ": "Symatics.measure",
    "π": "Symatics.project",
    "↔": "Symatics.entangle",
    "πₛ": "Symatics.πs",
}