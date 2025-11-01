# Glyph -> Lean operator bindings
# =========================================
# Defines canonical translation between
# Symatics glyph symbols (⊕, μ, ⟲, π, ↔, πs)
# and their corresponding Lean namespace functions.

GLYPH_TO_LEAN = {
    "⊕": "Symatics.superpose",
    "⟲": "Symatics.resonate",
    "μ": "Symatics.measure",
    "π": "Symatics.project",
    "↔": "Symatics.entangle",
    "πs": "Symatics.πs",
}