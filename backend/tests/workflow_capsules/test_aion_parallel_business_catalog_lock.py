from backend.modules.aion_gateway.parallel_catalog import (
    PARALLEL_CATALOG_PROTOCOL_VERSION,
    SETTLEMENT_MODE_FIAT_FIRST,
    ServiceArea,
    ServiceEvidenceRequirement,
    ServicePricingRule,
    ParallelServiceCatalogItem,
    ParallelBusinessProfile,
    build_home_fixed_parallel_catalog_preview,
)


def test_home_fixed_parallel_catalog_preview_has_required_identity():
    out = build_home_fixed_parallel_catalog_preview()

    assert out["protocol_version"] == PARALLEL_CATALOG_PROTOCOL_VERSION
    assert out["business_id"] == "home_fixed"
    assert out["business_name"] == "Home Fixed"
    assert out["vertical_key"] == "home_repair"
    assert isinstance(out["catalog_hash"], str)
    assert len(out["catalog_hash"]) == 64


def test_home_fixed_catalog_contains_core_home_repair_services():
    out = build_home_fixed_parallel_catalog_preview()
    services = out["services"]

    assert "general_home_repair" in services
    assert "roof_leak_repair" in services
    assert "painting_decorating" in services
    assert "pergola_canopy_repair" in services


def test_home_fixed_catalog_is_fiat_first_and_proof_required():
    out = build_home_fixed_parallel_catalog_preview()

    assert out["settlement_mode"] == SETTLEMENT_MODE_FIAT_FIRST
    assert out["proof_required"] is True
    assert out["human_review_required"] is True


def test_home_fixed_catalog_declares_service_area():
    out = build_home_fixed_parallel_catalog_preview()
    area = out["service_areas"][0]

    assert area["country"] == "Spain"
    assert "Almeria" in area["region"]
    assert "Arboleas" in area["towns"]
    assert "Albox" in area["towns"]


def test_service_catalog_hash_is_order_independent_for_service_dict_output():
    first = build_home_fixed_parallel_catalog_preview()
    second = build_home_fixed_parallel_catalog_preview()

    # created_at_ms can differ, so force same timestamp before comparing custom objects.
    profile_a = ParallelBusinessProfile(
        business_id="home_fixed",
        business_name="Home Fixed",
        vertical_key="home_repair",
        created_at_ms=123,
        service_areas=[ServiceArea(country="Spain", region="Almeria", towns=["A", "B"])],
        services=[
            ParallelServiceCatalogItem(
                service_key="b_service",
                title="B Service",
                category="test",
                pricing=ServicePricingRule(currency="EUR", base_price_minor=1000),
                evidence_requirements=[ServiceEvidenceRequirement("photo")],
            ),
            ParallelServiceCatalogItem(
                service_key="a_service",
                title="A Service",
                category="test",
                pricing=ServicePricingRule(currency="EUR", base_price_minor=2000),
                evidence_requirements=[ServiceEvidenceRequirement("photo")],
            ),
        ],
    )

    profile_b = ParallelBusinessProfile(
        business_id="home_fixed",
        business_name="Home Fixed",
        vertical_key="home_repair",
        created_at_ms=123,
        service_areas=[ServiceArea(country="Spain", region="Almeria", towns=["A", "B"])],
        services=list(reversed(profile_a.services)),
    )

    assert profile_a.to_dict()["catalog_hash"] == profile_b.to_dict()["catalog_hash"]


def test_catalog_hash_changes_when_service_data_changes():
    profile_a = ParallelBusinessProfile(
        business_id="home_fixed",
        business_name="Home Fixed",
        vertical_key="home_repair",
        created_at_ms=123,
        services=[
            ParallelServiceCatalogItem(
                service_key="repair",
                title="Repair",
                category="home",
                pricing=ServicePricingRule(currency="EUR", base_price_minor=1000),
            )
        ],
    )

    profile_b = ParallelBusinessProfile(
        business_id="home_fixed",
        business_name="Home Fixed",
        vertical_key="home_repair",
        created_at_ms=123,
        services=[
            ParallelServiceCatalogItem(
                service_key="repair",
                title="Repair",
                category="home",
                pricing=ServicePricingRule(currency="EUR", base_price_minor=2000),
            )
        ],
    )

    assert profile_a.to_dict()["catalog_hash"] != profile_b.to_dict()["catalog_hash"]


def test_parallel_catalog_has_no_live_side_effects():
    out = build_home_fixed_parallel_catalog_preview()
    safety = out["safety"]

    assert safety["would_create_booking"] is False
    assert safety["would_create_payment"] is False
    assert safety["would_create_escrow"] is False
    assert safety["would_expose_public_route"] is False
    assert safety["would_execute_goal_engine"] is False
