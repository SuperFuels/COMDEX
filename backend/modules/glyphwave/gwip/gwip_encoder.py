def encode_gwip_packet(wave, carrier_type, modulation_strategy, latency_ms=0.0, coherence=1.0):
    """
    Encode a GWIP packet from a WaveState-like object,
    embedding carrier and modulation metadata for transmission.
    """

    return {
        "wave_id": wave.id,
        "glyph_data": wave.glyph_data,
        "timestamp": wave.timestamp,

        # 📡 Carrier Metadata
        "carrier_type": getattr(carrier_type, "name", str(carrier_type)),
        "modulation_strategy": getattr(modulation_strategy, "name", str(modulation_strategy)),
        "latency_ms": round(latency_ms, 3),
        "coherence": round(coherence or wave.coherence or 1.0, 4),

        # 🔒 Optional encryption metadata
        "qkd_required": getattr(wave, "qkd_required", False),
        "gkey_id": getattr(wave, "gkey_id", None),
        "encrypted": getattr(wave, "encrypted", False),

        # 🌐 Metadata passthrough
        "metadata": {
            **(wave.metadata or {}),
        }
    }