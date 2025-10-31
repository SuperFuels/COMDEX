import asyncio
import pytest

from backend.modules.photonlang.parallel_capsules import ParallelCapsuleExecutor

@pytest.mark.asyncio
async def test_parallel_capsules_basic():
    exec = ParallelCapsuleExecutor(max_parallel=2)

    for i in range(4):
        exec.submit({"id": f"cap-{i}", "opcode": "⊕", "args": ["a", "b"]})

    task = asyncio.create_task(exec.run())
    await asyncio.sleep(0.2)
    exec.stop()
    await task

    # All executed, no errors implied by crashes
    assert len(exec.queue) == 0
    assert len(exec.running) == 0