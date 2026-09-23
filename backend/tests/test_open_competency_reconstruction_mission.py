from backend.modules.hexcore.open_competency_reconstruction_mission import (
    _component_evaluation,
    _normalise_artifact,
)


PLANNER = '''def build_plan(tasks, capabilities):
    levels = {"unassessed": 0, "beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}
    by_id = {}
    for task in tasks:
        if task["id"] in by_id: raise ValueError("duplicate")
        by_id[task["id"]] = task
    if any(dep not in by_id for task in tasks for dep in task.get("depends_on", [])):
        raise ValueError("unknown dependency")
    remaining = set(by_id); completed = set(); result = []
    while remaining:
        ready = [by_id[key] for key in remaining if set(by_id[key].get("depends_on", [])) <= completed]
        if not ready: raise ValueError("cycle")
        ready.sort(key=lambda row: (-row.get("priority", 0), row["id"]))
        task = ready[0]; capability = task.get("capability")
        if capability and levels.get(capabilities.get(capability, "unassessed"), 0) < 2:
            result.append("learn:" + capability)
        result.append(task["id"]); completed.add(task["id"]); remaining.remove(task["id"])
    return result
'''


RUNNER = '''class MissionRunner:
    def __init__(self, plan, max_attempts=2):
        self.plan=list(plan); self.max_attempts=max_attempts; self.position=0; self.attempts={}; self.completed=[]
    def next_task(self):
        return None if self.position >= len(self.plan) else self.plan[self.position]
    def record(self, task_id, success):
        if task_id != self.next_task(): raise ValueError("unexpected task")
        if success:
            self.completed.append(task_id); self.position += 1
        else:
            self.attempts[task_id] = self.attempts.get(task_id, 0) + 1
            if self.attempts[task_id] >= self.max_attempts: raise RuntimeError("attempts exhausted")
    def snapshot(self):
        return {"position":self.position,"attempts":self.attempts,"completed":self.completed,"max_attempts":self.max_attempts}
    @classmethod
    def from_snapshot(cls, plan, snapshot):
        obj=cls(plan, snapshot["max_attempts"]); obj.position=snapshot["position"]
        obj.attempts=dict(snapshot["attempts"]); obj.completed=list(snapshot["completed"]); return obj
    @property
    def complete(self): return self.position >= len(self.plan)
'''


def test_recursive_code_components_are_executable_and_composable():
    assert _component_evaluation("python_planner", PLANNER)["passed"]
    assert _component_evaluation("python_runner", RUNNER)["passed"]
    assert _component_evaluation("python_code", PLANNER + "\n" + RUNNER)["passed"]


def test_code_fence_normalisation_does_not_repair_semantics():
    wrapped = '{"code": "```python\\ndef f():\\n    return 1\\n```"}'
    import json
    assert _normalise_artifact("python_code", json.loads(wrapped)) == "def f():\n    return 1"
    unsafe = _normalise_artifact("python_code", {"code": "```python\nimport os\n```"})
    assert "import os" in unsafe

