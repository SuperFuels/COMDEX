from pathlib import Path

from backend.modules.local_node.local_node_runtime import (
    LocalNodeRuntime,
    _attach_governed_web_sources,
    _friendly_provider_failure,
    _verified_unit_total,
)
from backend.modules.local_node.contracts_local_node import (
    DeploymentMode,
    LocalNodeConfig,
)
from backend.services.aion_mission_mode import pilot_local_model_runtime


ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop" / "mac" / "src" / "app.js"
RUNTIME = ROOT / "backend" / "modules" / "local_node" / "local_node_runtime.py"


def test_unit_price_questions_use_verified_arithmetic() -> None:
    assert _verified_unit_total("what is 1000 customers at $50 per customer") == (
        "1000 × $50 = $50,000."
    )


def test_provider_failures_do_not_expose_runtime_diagnostics() -> None:
    failure = _friendly_provider_failure(
        "local_model",
        RuntimeError("connection refused at 127.0.0.1:11434/api/generate"),
    )
    assert failure["error_code"] == "local_model_unavailable"
    assert "127.0.0.1" not in failure["user_message"]
    assert "runtime is not ready" in failure["user_message"]


def test_local_context_limit_is_not_misreported_as_disconnected() -> None:
    failure = _friendly_provider_failure(
        "local_model",
        RuntimeError("local_model_context_limit_exceeded"),
    )
    assert failure["error_code"] == "local_model_context_limit"
    assert "conversation is too large" in failure["user_message"]
    assert "runtime is not ready" not in failure["user_message"]


def test_governed_web_sources_replace_partial_model_source_tail() -> None:
    answer = _attach_governed_web_sources(
        "Current coverage is summarised here [1].\n\nSources:\n1. broken partial URL",
        [
            {"title": "Verified report", "url": "https://example.com/report"},
            {"title": "Second source", "url": "https://example.org/news"},
        ],
    )
    assert "broken partial URL" not in answer
    assert "[Verified report](https://example.com/report)" in answer
    assert "[Second source](https://example.org/news)" in answer


def test_gemini_chat_uses_the_connected_gemini_route() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    assert 'if clean_provider in {"gemini", "google"}' in source
    assert "return self._call_gemini_chat(prompt=prompt)" in source


def test_chat_ui_uses_shared_workspace_and_branded_provider_errors() -> None:
    source = APP.read_text(encoding="utf-8")
    assert "getAionChatWorkspaceIdV1" in source
    assert "reached its conversation limit" in source
    assert "function renderAionChatMessageCopyV1" in source
    assert "data-aion-chat-external-url" in source
    assert "openExternalUrl" in source
    assert "aion-chat-citation-v1" in source
    assert "models.find((model) => model?.isLead === true)" in source
    assert "window.__aionChatLeadAppliedV1" in source
    assert "/api/boardroom/providers/status?workspace_id=" in source
    assert 'kind: "provider_error"' in source
    assert "aion-chat-error-actions-v1" in source
    assert 'data-tab="vault">Open Connections' in source
    assert "inset:58px 0 0 0!important" in source
    assert "display:flex; flex-direction:column" in source
    assert "overflow:hidden!important; background:#f7f9fc" in source
    assert "position:sticky; z-index:5; bottom:0" in source
    assert "scrollbar-color:#9bbcf5 transparent" in source
    assert "function scrollAionChatToLatestMessageV1()" in source
    assert "stream.scrollTop = stream.scrollHeight" in source


def test_chat_connection_hydration_does_not_repaint_for_each_status_request() -> None:
    source = APP.read_text(encoding="utf-8")
    assert "function scheduleAionChatConnectionHydrationV1()" in source
    assert "window.__aionChatConnectionHydrationScheduledV1" in source
    assert 'refreshAionVaultAiProviderStatusV1({ render: false })' in source
    assert 'refreshAionVaultLocalModelsV1({ render: false })' in source
    assert "await Promise.allSettled([" in source
    assert 'async function refreshAionVaultAiProviderStatusV1({ render: shouldRender = true } = {})' in source
    assert 'async function refreshAionVaultLocalModelsV1({ render: shouldRender = true } = {})' in source


def test_business_chat_context_is_bounded_for_local_and_free_api_models(tmp_path) -> None:
    runtime = LocalNodeRuntime(
        LocalNodeConfig(
            node_id="test-node",
            workspace_id="home-fixed",
            deployment_mode=DeploymentMode.LOCAL_FIRST,
            base_dir=str(tmp_path),
        )
    )
    prompt = runtime._build_aion_business_context_prompt(
        prompt="Are you working?",
        provider="gemini",
        dashboard_summary={"embedded": "x" * 2_000_000},
    )
    assert len(prompt) < 14_000
    assert "...[trimmed]" in prompt
    assert prompt.endswith("Are you working?")

    local_prompt = runtime._build_aion_business_context_prompt(
        prompt="Are you working?",
        provider="local_model",
        dashboard_summary={"embedded": "x" * 2_000_000},
    )
    assert len(local_prompt) < 6_500
    assert "...[trimmed]" in local_prompt
    assert local_prompt.endswith("Are you working?")


def test_business_chat_routes_only_latest_turn_into_model_prompt() -> None:
    source = RUNTIME.read_text(encoding="utf-8")
    call_start = source.index("final_prompt = self._build_aion_business_context_prompt(")
    call_end = source.index("\n            )", call_start)
    call_source = source[call_start:call_end]
    assert "prompt=intent_prompt" in call_source
    assert "prompt=clean_prompt" not in call_source


def test_active_business_can_use_device_approved_canonical_local_model(monkeypatch) -> None:
    selections = {
        "costa-conexion": {},
        "home-fixed": {
            "source": "local_model_vault",
            "selection_status": "selectable",
            "model_id": "qwen3-8b-fast-local-q4",
        },
    }
    monkeypatch.setattr(
        "backend.modules.aion_inference.local_model_selection_store.load_local_model_selection",
        lambda workspace_id: selections.get(workspace_id, {}),
    )
    monkeypatch.setattr(
        "backend.modules.aion_inference.local_model_vault.LocalModelVault.snapshot",
        lambda _self: {
            "models": [{
                "model_id": "qwen3-8b-fast-local-q4",
                "runtime_profile": {
                    "adapter": "openai_compatible_bounded_chat.v1",
                    "endpoint": "http://127.0.0.1:8897",
                    "finance_arithmetic": "verified_tessaris_tools_required",
                },
                "installations": [{
                    "model_path": __file__,
                    "model_sha256": "a" * 64,
                    "warehouse": {"verified": True},
                }],
            }],
        },
    )
    profile = pilot_local_model_runtime.selected_local_runtime_profile_for_workspace("costa-conexion")
    assert profile["model_id"] == "qwen3-8b-fast-local-q4"
    assert profile["endpoint"] == "http://127.0.0.1:8897"
