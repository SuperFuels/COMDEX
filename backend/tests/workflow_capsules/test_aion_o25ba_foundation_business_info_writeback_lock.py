from pathlib import Path


APP = Path("desktop/mac/src/app.js")


def source() -> str:
    return APP.read_text(encoding="utf-8")


def test_o25ba_writeback_function_exists():
    text = source()

    assert (
        "function persistFoundationPacketToBusinessInfoO25BA"
        in text
    )

    assert (
        "BEGIN AION O25BA FOUNDATION PACKET BUSINESS INFO WRITEBACK LOCK"
        in text
    )


def test_o25ba_maps_foundation_packet_into_business_info_fields():
    text = source()

    required = [
        'assign("business_name", source.business_name);',
        'assign("website", source.website_url);',
        'assign("products_services", source.offer_summary);',
        'assign("target_customers", source.customer_type);',
        'assign("revenue_streams", source.revenue_streams);',
        'assign("current_tools", source.current_tools_and_evidence);',
        'assign("current_pain_points", source.current_challenges);',
        'assign("growth_goals", source.near_term_priorities);',
        "state.smallBusinessFoundationDraft",
        "state.businessContextFoundation",
    ]

    for token in required:
        assert token in text


def test_o25ba_persists_voice_scan_and_final_handoff():
    text = source()

    assert '"foundation_voice_turn"' in text
    assert '"foundation_website_scan"' in text
    assert '"foundation_finance_handoff"' in text
    assert "approved: true" in text


def test_o25ba_writes_keys_read_by_business_context_surface():
    text = source()

    required_keys = [
        "aion.smallBusinessFoundationDraft",
        "aion.businessContextFoundation",
        "aion.smallBusinessFoundation.draft.v1",
        "aion.smallBusinessFoundation.context.v1",
        "aion.businessFoundation.context.v1",
        "aion.businessContext.v1",
        "aion.approvedSmallBusinessFoundation",
        "aion.smallBusinessFoundation.approvedContext.v1",
    ]

    for key in required_keys:
        assert key in text
