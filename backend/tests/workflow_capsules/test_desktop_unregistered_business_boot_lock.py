from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = (ROOT / "desktop/mac/src/lib/desktop-state-contracts.js").read_text(
    encoding="utf-8"
)
MAIN = (ROOT / "desktop/mac/electron/main.js").read_text(encoding="utf-8")
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
RUNTIME_ADAPTER = (ROOT / "desktop/mac/src/desktop-runtime-adapter.js").read_text(
    encoding="utf-8"
)
BUSINESS_CLIENT = (
    ROOT / "desktop/mac/src/aion_business_container_client.js"
).read_text(encoding="utf-8")
PRELOAD = (ROOT / "desktop/mac/electron/preload.js").read_text(encoding="utf-8")


def test_clean_renderer_boots_without_demo_business_authority():
    assert 'var DEFAULT_WORKSPACE_ID = "business-not-registered";' in CONTRACTS
    assert 'var DEFAULT_WORKSPACE_ID = "costa-conexion";' not in CONTRACTS


def test_clean_main_process_does_not_default_custom_departments_to_demo_business():
    assignment = (
        'const AION_CUSTOM_DEPARTMENT_WORKSPACE_ID = '
        'process.env.TESSARIS_FOUNDER_WORKSPACE_ID || "business-not-registered";'
    )
    assert assignment in MAIN


def test_clean_renderer_does_not_hydrate_runtime_or_recovery_for_unregistered_business():
    guard = 'if (!canonicalWorkspaceId) {'
    assert guard in RUNTIME_ADAPTER
    assert 'workspaceId: "business-not-registered"' in RUNTIME_ADAPTER
    assert guard in APP
    assert 'window.AionBusinessContainerClient?.resolveBusinessId?.() || ""' in APP


def test_registered_business_identity_is_restored_from_os_protected_binding():
    assert 'ipcRenderer.invoke("aion-business-vault-identity-get")' in PRELOAD
    assert "await global.aionDesktop.getBusinessVaultIdentity()" in BUSINESS_CLIENT
    assert "publishBusinessIdentity(businessId, binding.business_name)" in BUSINESS_CLIENT
    assert 'window.addEventListener("aion:business-identity-established"' in APP


def test_business_container_requests_follow_the_isolated_desktop_backend():
    assert "global.aionDesktop?.backendApiBase" in BUSINESS_CLIENT
    assert "fetch(`${apiBase()}${path}`" in BUSINESS_CLIENT
    assert "const API_BASE = 'http://127.0.0.1:8080'" not in BUSINESS_CLIENT


def test_finance_handoff_routes_before_optional_local_voice_playback():
    handoff = APP.index("if (isFinanceHandoff) {", APP.index("async function speakNextQuestionFromPacketO25AJ"))
    speech = APP.index("const result = await speakLocalO25AJ(", handoff)
    assert handoff < speech


def test_completed_foundation_defers_unrelated_operational_hydration_until_finance_setup():
    assert "function shouldDeferOperationalHydrationForFoundationHandoff()" in APP
    assert "if (shouldDeferOperationalHydrationForFoundationHandoff())" in APP
    assert "const financeSetupPending" in APP
    assert "financeSetupPending && typeof window.AionFinancePilot?.render" in APP
    assert "await window.AionBusinessContainerClient?.whenReady?.();" in APP
    assert "whenReady: () => bootstrapReady" in BUSINESS_CLIENT
    assert "hydrateFinanceState, hydrateTrainAgentWorkspaceState, hydrateFounderNotes" in BUSINESS_CLIENT
