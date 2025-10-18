CFA_SCHEMAS["symatics/resonance_coupling"] = {
    "description": "Live Φ–ψ resonance coupling telemetry emitted by Morphic Ledger.",
    "version": "1.0",
    "fields": {
        "count":        {"type": "int", "desc": "Number of samples in the current window"},
        "Φ_mean":       {"type": "float", "desc": "Mean Φ awareness amplitude"},
        "ψ_mean":       {"type": "float", "desc": "Mean ψ wave field amplitude"},
        "correlation":  {"type": "float", "desc": "Φ–ψ Pearson correlation coefficient"},
        "phase_diff":   {"type": "float", "desc": "Mean absolute Φ–ψ phase difference"},
        "resonance_index": {"type": "float", "desc": "Composite resonance stability index"},
        "timestamp":    {"type": "float", "desc": "Timestamp of most recent sample"}
    },
    "tags": ["Φψ", "resonance", "coupling", "morphic", "QFC"],
    "emitters": ["MORPHIC_LEDGER"],
    "consumers": ["GHXVisualizer", "QFCController", "TessarisMetrics"]
}