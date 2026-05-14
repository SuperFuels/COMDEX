"""
PhotonLang ⧖ - Parametric Modulation Operator
Applies harmonic shaping to resonance output.
"""

def modulate(wave: dict, params: dict):
    # protect against missing fields
    wave = dict(wave)  # shallow safe copy

    freq = wave.get("frequency", 1)
    amp  = wave.get("amplitude", 1)

    # pull modifiers
    df = params.get("freq", 1.0)
    da = params.get("amp", 1.0)

    # gentle envelope - prevent runaway energy
    df = max(0.95, min(df, 1.05))
    da = max(0.95, min(da, 1.05))

    wave["frequency"] = freq * df
    wave["amplitude"] = amp * da

    # add modulation telemetry
    wave["modulation"] = {
        "Δfreq": df,
        "Δamp": da
    }

    return wave