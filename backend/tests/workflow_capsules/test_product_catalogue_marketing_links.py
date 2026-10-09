from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORKSPACE = (ROOT / "desktop/mac/src/aion_operating_model_workspace.js").read_text(encoding="utf-8")
IMPORT_API = (ROOT / "backend/modules/aion_business/api/business_twin_data_api.py").read_text(encoding="utf-8")
LOCAL_NODE_API = (ROOT / "backend/api/local_node_router.py").read_text(encoding="utf-8")


def test_products_and_services_store_marketing_catalogue_metadata():
    for marker in (
        "Product / service details",
        "data-om-offering-details",
        "product_url",
        "primary_image_url",
        "image_urls",
        "catalogue_source",
        "external_id",
        "data-om-offering-images",
        "multiple data-om-offering-images",
        "resolveImageUrl: catalogueImageSource",
        "/api/local-node/marketing/assets/",
        "Connect or map a store",
    ):
        assert marker in WORKSPACE

    assert "Marketing and online catalogue details" not in WORKSPACE
    assert 'role="dialog"' in WORKSPACE


def test_catalogue_import_preserves_store_identity_image_and_destination():
    for marker in (
        '"product_url"',
        '"primary_image_url"',
        '"catalogue_source"',
        '"external_id"',
        '"shopify_product_id"',
        '"woocommerce_product_id"',
    ):
        assert marker in IMPORT_API


def test_marketing_api_accepts_governed_catalogue_provenance():
    for field in (
        "subject_offering_id",
        "subject_offering_name",
        "product_url",
        "product_image_url",
        "catalogue_source",
        "external_product_id",
    ):
        assert f"{field}: Optional[str]" in LOCAL_NODE_API
    assert 'brief: str = ""' in LOCAL_NODE_API


def test_uploaded_catalogue_images_are_served_from_the_owning_workspace():
    assert '@router.get("/marketing/assets/{stored_name}")' in LOCAL_NODE_API
    assert "candidate.parent != upload_dir" in LOCAL_NODE_API
    assert 'return FileResponse(candidate)' in LOCAL_NODE_API
