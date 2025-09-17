import asyncio
import random
from time import perf_counter
from typing import Dict, Any

# Mock broadcast function (simulate broadcast_qfc_update)
async def mock_broadcast_qfc_update(container_id: str, payload: Dict[str, Any]):
    print(f"\n📡 [Mock Broadcast] container: {container_id}")
    print("Payload:", payload)
    await asyncio.sleep(0.05)  # simulate network delay


# Simulate a GlyphCell
class MockCell:
    def __init__(self, cell_id: str):
        self.id = cell_id
        self.logic = random.choice(["⊕", "↔", "⟲", "→", "⊗"])
        self.sqi_score = round(random.random(), 3)
        self.prediction_forks = []
        self.result = None


async def simulate_cell_execution(container_id: str, cell: MockCell):
    # Simulate execution timing
    start_time = perf_counter()
    token_metrics = {}
    opcode_metrics = {}

    # Simulate per-token execution
    for token in ["⊕", "↔", "⟲", "→", "⊗"]:
        token_start = perf_counter()
        # random FP times
        fp4 = random.uniform(0.0001, 0.001)
        fp8 = random.uniform(0.0001, 0.001)
        int8 = random.uniform(0.0001, 0.001)
        total = perf_counter() - token_start

        token_metrics[token] = [{"total": total, "fp4": fp4, "fp8": fp8, "int8": int8}]
        opcode_metrics[token] = {
            "count": random.randint(1, 3),
            "total_time": total,
            "fp4_time": fp4,
            "fp8_time": fp8,
            "int8_time": int8
        }

    elapsed = perf_counter() - start_time

    # Broadcast
    await mock_broadcast_qfc_update(container_id, {
        "type": "qpu_cell_update",
        "cell_id": cell.id,
        "sqi": cell.sqi_score,
        "mutation_count": random.randint(0, 5),
        "exec_time": elapsed,
        "last_result": f"Result({cell.logic})",
        "token_metrics": token_metrics,
        "opcode_breakdown": opcode_metrics
    })


async def simulate_sheet(container_id: str, num_cells: int = 5):
    cells = [MockCell(f"cell_{i}") for i in range(num_cells)]
    for cell in cells:
        await simulate_cell_execution(container_id, cell)
        await asyncio.sleep(0.1)  # spacing between broadcasts


if __name__ == "__main__":
    container_id = "test_container"
    print(f"🚀 Starting terminal test for LiveQpuCpuPanel (container={container_id})...")
    asyncio.run(simulate_sheet(container_id, num_cells=5))
    print("\n✅ Terminal simulation complete.")