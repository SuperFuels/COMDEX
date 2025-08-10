def test_upgrade_downgrade_roundtrip():
    from backend.modules.glyphwave.gwip_codec import GWIPCodec
    codec = GWIPCodec()
    gip = {"type":"gip","channel":"luxnet","payload":{"hello":"world"}}
    gwip = codec.upgrade(gip)
    back = codec.downgrade(gwip)
    assert back == gip