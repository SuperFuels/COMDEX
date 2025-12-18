import pytest

@pytest.mark.asyncio
async def test_reset_wires_validator_registry():
    from backend.modules.chain_sim.chain_sim_routes import chain_sim_dev_reset, DevResetRequest, DevGenesisAlloc, DevGenesisValidator

    body = DevResetRequest(
        chain_id="glyphchain-dev",
        network_id="devnet",
        allocs=[DevGenesisAlloc(address="pho1-dev-val1", balances={"TESS":"1000","PHO":"1000"})],
        validators=[DevGenesisValidator(address="pho1-dev-val1", self_delegation_tess="100", commission="0")],
    )

    resp = await chain_sim_dev_reset(body)

    # JSONResponse path
    import json
    payload = json.loads(resp.body.decode("utf-8"))
    assert payload["ok"] is True
    assert payload["applied_validators"] == 1
    assert len(payload.get("validators") or []) == 1

    # validator_registry path (best-effort: adapt if your module exposes different getter)
    from backend.modules.chain_sim import validator_registry as vr
    if hasattr(vr, "get_validators"):
        vals = vr.get_validators()
        assert isinstance(vals, list) and len(vals) == 1