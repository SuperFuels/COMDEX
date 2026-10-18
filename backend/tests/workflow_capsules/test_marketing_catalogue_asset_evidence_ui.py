from pathlib import Path


APP = (Path(__file__).resolve().parents[3] / "desktop/mac/src/app.js").read_text(encoding="utf-8")
ROUTER = (Path(__file__).resolve().parents[3] / "backend/api/local_node_router.py").read_text(encoding="utf-8")
RUNTIME = (Path(__file__).resolve().parents[3] / "backend/modules/local_node/local_node_runtime.py").read_text(encoding="utf-8")
WORKFLOW_RUNTIME = (
    Path(__file__).resolve().parents[3]
    / "backend/modules/aion_agents/runtime/workflow_execution_runtime.py"
).read_text(encoding="utf-8")
IMAGE_SERVICE = (
    Path(__file__).resolve().parents[3]
    / "backend/modules/aion_business/runtime/image_generation_service.py"
).read_text(encoding="utf-8")


def test_saved_product_image_counts_as_campaign_evidence() -> None:
    assert "const catalogueAsset = aionMarketingOfferingAsset(selectedOffering);" in APP
    assert "|| Boolean(catalogueAsset)" in APP
    assert "product image will be used automatically" in APP


def test_saved_product_image_is_visible_in_the_create_asset_list() -> None:
    assert 'source: "product_catalogue"' in APP
    assert "PRODUCT IMAGE" in APP
    assert "ATTACHED TO DRAFT" in APP


def test_missing_evidence_message_tells_the_user_exactly_what_to_do() -> None:
    assert "No usable source image is attached. Add a product image under Product / service details" in APP


def test_toolbar_model_choice_reaches_the_marketing_workflow() -> None:
    assert "selected_provider: activeModel?.provider_id || undefined" in APP
    assert "selected_model: activeModel?.model_id || undefined" in APP
    assert "selected_provider: Optional[str] = None" in ROUTER
    assert "selected_provider=request.selected_provider" in ROUTER
    assert '"selected_provider": selected_provider' in RUNTIME


def test_marketing_generation_forbids_unsupported_product_claims() -> None:
    assert "Use only explicitly supplied or verified facts for claims." in WORKFLOW_RUNTIME
    assert "Never invent product qualities" in WORKFLOW_RUNTIME
    assert "free services" in WORKFLOW_RUNTIME


def test_existing_draft_can_be_regenerated_with_its_attached_evidence() -> None:
    assert "function getAionMarketingExistingSourceAssets()" in APP
    assert "existingSourceAssets.length > 0" in APP
    assert "Regenerate current draft" in APP
    assert "data-aion-run-manual-marketing" in APP
    assert "data-aion-regenerate-marketing-draft" in APP
    assert "async function regenerateAionMarketingCampaign" in APP
    assert '"creative_assets",' in ROUTER
    assert '"creative_direction",' in ROUTER
    assert "Choose a connected model from the MODEL menu" in APP


def test_marketing_creator_exposes_format_style_and_creation_method() -> None:
    assert 'facebook_feed: { label: "Facebook single image", formatLabel: "Single image post"' in APP
    assert 'instagram_carousel: { label: "Instagram carousel", formatLabel: "Carousel"' in APP
    assert "const MARKETING_PLATFORM_FORMATS" in APP
    for format_label in ("Single image post", "Carousel", "Story", "Reel / video"):
        assert format_label in APP
    for style in (
        "product_showcase",
        "minimal_editorial",
        "bold_promotion",
        "customer_story",
        "proof_focus",
        "brand_led",
    ):
        assert style in APP
        assert style in IMAGE_SERVICE
    assert "data-marketing-design-style" in APP
    assert "data-marketing-creation-method" in APP
    assert "Apply style and regenerate current draft" in APP


def test_single_image_posts_do_not_expand_into_five_card_carousels() -> None:
    assert 'content_format: MARKETING_CREATE_TEMPLATES' in APP
    assert 'creative_direction.get("content_format") or "image"' in WORKFLOW_RUNTIME
    assert 'expected_cards = 5 if content_format == "carousel" else 1' in WORKFLOW_RUNTIME
    assert '"visual_type": content_format' in WORKFLOW_RUNTIME
    assert 'isCarousel = template ? template.format === "carousel"' in APP
    assert "postPackage.carousel = firstCard ? [firstCard] : []" in APP


def test_custom_platform_guidance_reaches_the_model_prompt() -> None:
    for field in ("canvas_size", "aspect_ratio", "copy_structure"):
        assert f"{field}: Optional[str] = None" in ROUTER
        assert f'"{field}": raw.get("{field}")' in WORKFLOW_RUNTIME
    assert "Required copy structure" in WORKFLOW_RUNTIME


def test_owned_media_renderer_uses_selected_template() -> None:
    assert 'creative_direction.get("design_template")' in IMAGE_SERVICE
    assert 'creative_direction.get("creation_method")' in IMAGE_SERVICE
    assert 'creation_method != "generate_new"' in IMAGE_SERVICE
    assert '"model": f"evidence-rendition-v2:{design_style}"' in IMAGE_SERVICE
