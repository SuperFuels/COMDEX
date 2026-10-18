from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text()
BACKEND = (ROOT / "desktop/mac/src/aion_department_pilot_backend.js").read_text()
INBOX = (ROOT / "desktop/mac/src/aion_finance_inbox_workspace.js").read_text()
SALES = (ROOT / "desktop/mac/src/aion_finance_sales_workspace.js").read_text()


def test_finance_uses_full_width_resizable_command_centre():
    assert 'function renderFinancePilotCommandCentre(financeWorkspace = "")' in APP
    assert 'data-aion-finance-command-centre="true"' in APP
    assert 'data-aion-finance-split="34"' in APP
    assert 'data-aion-finance-split-handle="true"' in APP
    assert 'minmax(330px,${next}fr) 30px minmax(620px,${100 - next}fr)' in APP
    assert 'position:fixed!important;top:88px!important;left:64px!important;right:0!important;bottom:0!important' in APP


def test_finance_chat_and_functionality_have_separate_panes():
    assert 'data-aion-finance-pilot-pane="true"' in APP
    assert 'data-aion-finance-conversation-thread="true"' in APP
    assert 'data-aion-finance-pilot-input="true"' in APP
    assert 'data-aion-finance-pilot-send="true"' in APP
    assert 'data-aion-finance-workspace-pane="true"' in APP
    assert 'data-aion-finance-functional-workspace="true">${renderAionFinanceFunctionalWorkspaceV1(financeWorkspace)}' in APP
    assert '[data-aion-finance-workspace-pane] [data-aion-pilot-role="finance"]>.aion-pilot-composer-bar' in APP


def test_finance_owns_financial_foundations_from_the_shared_operating_model():
    operating_model = (ROOT / "desktop/mac/src/aion_operating_model_workspace.js").read_text()

    assert 'data-aion-finance-functional-section="foundations"' in APP
    assert 'function renderAionFinanceFoundationsV1()' in APP
    assert "operatingModel.renderFinanceFoundations?.()" in APP
    assert "Save & update Boardroom" in APP
    assert "renderFinanceFoundations: () => finance({ embeddedInFinance:true })" in operating_model


def test_grounded_finance_conversation_is_routed_to_left_pane():
    assert "const conversationStream = commandCentre?.querySelector?.('[data-aion-finance-conversation-thread]') || stream;" in BACKEND
    assert "stream.querySelector?.('[data-aion-finance-conversation]')?.remove?.();" in BACKEND
    assert "[data-aion-finance-pilot-send],[data-aion-pilot-create-draft-mission]" in BACKEND
    assert "commandCentre?.querySelector?.('[data-aion-finance-pilot-input]')" in BACKEND


def test_finance_workspace_starts_with_cash_position_and_not_package_card():
    assert '${key === "finance" ? "" : `<section' in APP
    assert 'Boardroom Package' in APP
    assert 'data-aion-finance-cash-position' in BACKEND
    assert 'data-aion-finance-cash-in-hand' in BACKEND
    assert 'data-aion-finance-save-cash-position' in BACKEND
    assert 'CASH IN BANK' in BACKEND
    assert 'CASH IN HAND' in BACKEND
    assert 'TOTAL AVAILABLE CASH' in BACKEND
    assert "stream.insertAdjacentHTML?.('afterbegin', financeDirectorPanel" in BACKEND
    assert "financeDirector.insertAdjacentHTML?.('afterend', html)" in BACKEND
    assert "if (financeDirector) financeDirector.insertAdjacentHTML('afterend', markup());" in INBOX
    assert "if (financeDirector) financeDirector.insertAdjacentHTML('afterend', markup());" in SALES
    assert "else anchor.insertAdjacentHTML('beforebegin', markup());" in SALES


def test_finance_embedded_workspaces_use_the_signal_palette():
    assert '[data-aion-finance-workspace-pane] .fsw-shell' in APP
    assert '[data-aion-finance-workspace-pane] .fiw-shell' in APP
    assert '--teal:#2563eb!important;--green:#2563eb!important' in APP
    assert '.fiw-shell button.primary' in APP
    assert '.fiw-tabs button.active' in APP
    assert '.fiw-document.status-approved_for_accounting' in APP
    assert 'border-radius:16px!important;background:#fff!important' in APP
    assert 'Read-only chat</span>' in APP
