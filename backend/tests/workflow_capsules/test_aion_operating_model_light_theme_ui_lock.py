from pathlib import Path


WORKSPACE = Path("desktop/mac/src/aion_operating_model_workspace.js")


def workspace_source() -> str:
    return WORKSPACE.read_text(encoding="utf-8")


def test_operating_model_owns_one_scoped_light_theme():
    source = workspace_source()

    assert "id='aion-operating-model-style'" in source
    assert "--om-paper:#ffffff" in source
    assert "background:var(--om-paper) !important" in source
    assert ".om-terminal" in source


def test_operating_model_controls_remain_high_contrast_inside_global_surface():
    source = workspace_source()

    assert ".om-shell .om-input" in source
    assert "color:var(--om-ink) !important" in source
    assert ".om-shell .om-add" in source
    assert "background:var(--om-green) !important" in source
    assert ".om-shell .om-tabs button[data-active=true]" in source
    assert "background:var(--om-teal) !important" in source


def test_all_operating_model_subtabs_continue_to_share_the_theme():
    source = workspace_source()

    assert "['workforce', 'Workforce & capacity']" in source
    assert "['jobs', 'Jobs & quotes']" in source
    assert '<section class="om-terminal">' in source
    assert '<div class="om-content">${content()}</div>' in source


def test_workforce_is_hr_linked_and_quoted_jobs_track_variance():
    source = workspace_source()

    assert "Select a person from HR" in source
    assert "confidential_hr_effective_planning_cost" not in source
    assert "Quoted jobs and project economics" in source
    assert "Variable job costs" in source
    assert "Estimate versus actual" in source
