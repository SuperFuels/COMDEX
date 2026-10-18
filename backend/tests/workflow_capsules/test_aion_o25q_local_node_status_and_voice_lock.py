from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
REPO = ROOT / "backend/modules/aion_agents/runtime/workflow_definition_repository.py"
APP = ROOT / "desktop/mac/src/app.js"


def test_o25q_workflow_repository_quarantines_empty_or_corrupt_json():
    text = REPO.read_text(encoding="utf-8")
    assert "AION O25Q empty/corrupt workflow quarantine" in text
    assert "if not raw.strip()" in text
    assert "_quarantine_invalid_workflow_file" in text
    assert "WorkflowDefinition.model_validate_json(raw)" in text
    assert "return None" in text


def test_o25q_final_single_local_voice_authority_installed():
    text = APP.read_text(encoding="utf-8")
    assert "AION O25Q — Final single local voice startup authority" in text
    assert "aion.o25q.final_single_local_voice_startup.v1" in text
    assert "aionO25QStartSingleLocalVoice" in text
    assert "provider: \"local\"" in text
    assert "http://127.0.0.1:8080/api/aion/voice/tts" in text
    assert "O25Q owns local startup voice" in text


def test_o25q_js_syntax():
    subprocess.run(["node", "--check", str(APP)], cwd=ROOT, check=True)
