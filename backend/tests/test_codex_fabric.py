import pytest
from backend.modules.codex.codex_fabric import CodexFabric
from backend.modules.codex.codex_core import CodexCore
from backend.modules.codex.codex_context_adapter import CodexContextAdapter

# Mock container logic for test
class MockContainer:
    def __init__(self, id, traits=None):
        self.id = id
        self.traits = traits or {}
        self.codex_core = CodexCore(container_id=id)

    def tick(self):
        return self.codex_core.execute_tick()

@pytest.fixture
def codex_fabric():
    fabric = CodexFabric()
    # Register two mock containers for testing
    fabric.register_container(MockContainer("test_container_1"))
    fabric.register_container(MockContainer("test_container_2"))
    return fabric

def test_container_registration(codex_fabric):
    assert "test_container_1" in codex_fabric.containers
    assert "test_container_2" in codex_fabric.containers

def test_parallel_execution(codex_fabric):
    results = codex_fabric.run_tick_all()
    assert "test_container_1" in results
    assert "test_container_2" in results
    assert isinstance(results["test_container_1"], dict)

def test_task_routing(codex_fabric):
    task = {"type": "dream", "payload": "Test dream task"}
    codex_fabric.route_task("test_container_1", task)
    assert codex_fabric.containers["test_container_1"].codex_core.task_queue[-1] == task

def test_dynamic_container_addition():
    fabric = CodexFabric()
    assert len(fabric.containers) == 0
    fabric.register_container(MockContainer("dynamic_container"))
    assert "dynamic_container" in fabric.containers