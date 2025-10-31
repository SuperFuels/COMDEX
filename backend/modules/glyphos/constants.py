# backend/modules/glyphos/constants.py
# 🔒 Single source of truth for glyph alphabet + defaults

# Frozen alphabet (keep in sync here only)
GLYPH_ALPHABET = (
    "⚛︎☯☀☾☽✦✧✩✪✫✬✭✮✯✰✱✲✳✴✵✶✷✸✹✺✻✼✽✾✿❀❁❂❃❄❅❆❇❈❉❊❋"
    "⊕↔∇⟲μπΦΨΩΣΔΛΘΞΓαβγδλστωηικ"
    "◇◆◧◨◩◪◫⬡⬢⬣⬤⟁⧖"
)

# Default/fallback glyph used when no specific mapping is found
DEFAULT_GLYPH = "✦"