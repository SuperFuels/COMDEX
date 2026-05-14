import os
import pytest
from backend.modules.glyphwave.core.wave_state import WaveState
from backend.modules.glyphwave.qwave.beam_controller import AdvancedBeamController


@pytest.fixture
def controller(tmp_path):
    cfg = {"tick_rate": 0.1, "enable_logging": True, "test_mode": True, "container_id": "test.dc"}
    ctl = AdvancedBeamController(cfg)
    ctl.qwave_writer.out_dir = tmp_path
    return ctl

def test_persistence_integration(controller):
    # Simulate a single wave tick
    ws = WaveState.from_container_id(controller.container_id)
    ws.evolve()
    controller.persist_snapshot(ws, 1)

    # Verify file created
    logs = controller.qwave_writer.list_logs()
    assert len(logs) == 1
    assert logs[0].endswith(".qwv")

def test_pmg_state_archival(controller):
    ws = WaveState.from_container_id(controller.container_id)
    ws.evolve()
    controller.persist_snapshot(ws, 2)
    state = controller.pmg.retrieve_capsule_state(ws.id)
    assert state is not None
    assert "sqi_score" in state