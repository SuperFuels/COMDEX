def modulate(wave, params):
    """
    PhotonLang ⧖ operator:
    - adjusts symbolic frequency & amplitude harmonics
    """

    wave = dict(wave)  # shallow copy safe for now
    wave["frequency"] = wave.get("frequency", 1) * params.get("freq", 1)
    wave["amplitude"] = wave.get("amplitude", 1) * params.get("amp", 1)
    return wave