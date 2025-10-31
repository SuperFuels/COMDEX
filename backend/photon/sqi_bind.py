from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

rmc = ResonantMemoryCache()

def bind_sqi(glyph):
    txt = glyph.get("text", "")
    entry = rmc.recall(txt.lower())
    if not entry:
        glyph["sqi"] = 0.1
        return glyph

    glyph["sqi"] = round(
        (entry.get("stability",0)
         + entry.get("coherence",0)
         + entry.get("SQI_avg",0)) / 3, 4
    )
    return glyph