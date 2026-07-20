from __future__ import annotations

from pathlib import Path


class AIONBusinessPaths:
    ROOT = Path(".runtime/AION_BUSINESS")

    WORKSPACES = ROOT / "workspaces"
    CONTAINER_BINDINGS = ROOT / "container_bindings"
    BUSINESS_CONTAINERS = ROOT / "business_containers"
    ROLES = ROOT / "roles"
    AGENTS = ROOT / "agents"
    TASKS = ROOT / "tasks"
    LEARNING = ROOT / "learning"
    AUDIT = ROOT / "audit"
    FOUNDER_REVIEW = ROOT / "founder_review"
    EXTERNAL_SPECIALISTS = ROOT / "external_specialists"
    EXTERNAL_WORK_ORDERS = ROOT / "external_work_orders"
    TOPOLOGIES = ROOT / "topologies"
    DEPARTMENT_PILOT_RUNTIME = ROOT / "department_pilot_runtime"

    @classmethod
    def ensure_base_dirs(cls) -> None:
        cls.ROOT.mkdir(parents=True, exist_ok=True)
        cls.WORKSPACES.mkdir(parents=True, exist_ok=True)
        cls.CONTAINER_BINDINGS.mkdir(parents=True, exist_ok=True)
        cls.BUSINESS_CONTAINERS.mkdir(parents=True, exist_ok=True)
        cls.ROLES.mkdir(parents=True, exist_ok=True)
        cls.AGENTS.mkdir(parents=True, exist_ok=True)
        cls.TASKS.mkdir(parents=True, exist_ok=True)
        cls.LEARNING.mkdir(parents=True, exist_ok=True)
        cls.AUDIT.mkdir(parents=True, exist_ok=True)
        cls.FOUNDER_REVIEW.mkdir(parents=True, exist_ok=True)
        cls.EXTERNAL_SPECIALISTS.mkdir(parents=True, exist_ok=True)
        cls.EXTERNAL_WORK_ORDERS.mkdir(parents=True, exist_ok=True)
        cls.TOPOLOGIES.mkdir(parents=True, exist_ok=True)
        cls.DEPARTMENT_PILOT_RUNTIME.mkdir(parents=True, exist_ok=True)

    @classmethod
    def workspace_file(cls, workspace_id: str) -> Path:
        cls.ensure_base_dirs()
        return cls.WORKSPACES / f"{workspace_id}.json"

    @classmethod
    def binding_dir(cls, workspace_id: str) -> Path:
        cls.ensure_base_dirs()
        path = cls.CONTAINER_BINDINGS / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def binding_file(cls, workspace_id: str, binding_id: str) -> Path:
        return cls.binding_dir(workspace_id) / f"{binding_id}.json"

    @classmethod
    def business_container_dir(cls, workspace_id: str) -> Path:
        cls.ensure_base_dirs()
        path = cls.BUSINESS_CONTAINERS / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def business_container_file(cls, workspace_id: str, container_kind: str) -> Path:
        return cls.business_container_dir(workspace_id) / f"{container_kind}.json"

    @classmethod
    def business_container_index_file(cls, workspace_id: str) -> Path:
        return cls.business_container_dir(workspace_id) / "_index.json"

    @classmethod
    def role_dir(cls, workspace_id: str) -> Path:
        cls.ensure_base_dirs()
        path = cls.ROLES / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def role_file(cls, workspace_id: str, role_id: str) -> Path:
        return cls.role_dir(workspace_id) / f"{role_id}.json"

    @classmethod
    def agent_dir(cls, workspace_id: str) -> Path:
        cls.ensure_base_dirs()
        path = cls.AGENTS / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def agent_file(cls, workspace_id: str, agent_id: str) -> Path:
        return cls.agent_dir(workspace_id) / f"{agent_id}.json"

    @classmethod
    def task_dir(cls, workspace_id: str) -> Path:
        cls.ensure_base_dirs()
        path = cls.TASKS / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def task_file(cls, workspace_id: str, task_id: str) -> Path:
        return cls.task_dir(workspace_id) / f"{task_id}.json"

    @classmethod
    def learning_dir(cls, workspace_id: str) -> Path:
        cls.ensure_base_dirs()
        path = cls.LEARNING / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def learning_file(cls, workspace_id: str, record_id: str) -> Path:
        return cls.learning_dir(workspace_id) / f"{record_id}.json"

    @classmethod
    def audit_dir(cls, workspace_id: str) -> Path:
        cls.ensure_base_dirs()
        path = cls.AUDIT / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def audit_file(cls, workspace_id: str, stream: str) -> Path:
        return cls.audit_dir(workspace_id) / f"{stream}.jsonl"

    @classmethod
    def founder_review_dir(cls, workspace_id: str) -> Path:
        cls.ensure_base_dirs()
        path = cls.FOUNDER_REVIEW / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def founder_review_config_file(cls, workspace_id: str) -> Path:
        return cls.founder_review_dir(workspace_id) / "config.json"

    @classmethod
    def external_specialist_dir(cls, workspace_id: str) -> Path:
        cls.ensure_base_dirs()
        path = cls.EXTERNAL_SPECIALISTS / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def external_specialist_file(cls, workspace_id: str, specialist_id: str) -> Path:
        return cls.external_specialist_dir(workspace_id) / f"{specialist_id}.json"

    @classmethod
    def external_work_order_dir(cls, workspace_id: str) -> Path:
        cls.ensure_base_dirs()
        path = cls.EXTERNAL_WORK_ORDERS / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def external_work_order_file(cls, workspace_id: str, work_order_id: str) -> Path:
        return cls.external_work_order_dir(workspace_id) / f"{work_order_id}.json"

    @classmethod
    def topology_dir(cls) -> Path:
        cls.ensure_base_dirs()
        cls.TOPOLOGIES.mkdir(parents=True, exist_ok=True)
        return cls.TOPOLOGIES

    @classmethod
    def topology_file(cls, workspace_id: str) -> Path:
        return cls.topology_dir() / f"{workspace_id}.json"

    @classmethod
    def department_pilot_dir(cls, workspace_id: str, department_id: str) -> Path:
        cls.ensure_base_dirs()
        path = cls.DEPARTMENT_PILOT_RUNTIME / workspace_id / department_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def department_pilot_task_dir(cls, workspace_id: str, department_id: str) -> Path:
        path = cls.department_pilot_dir(workspace_id, department_id) / "tasks"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def department_pilot_task_file(
        cls, workspace_id: str, department_id: str, task_id: str
    ) -> Path:
        return cls.department_pilot_task_dir(workspace_id, department_id) / f"{task_id}.json"

    @classmethod
    def department_pilot_audit_file(cls, workspace_id: str, department_id: str) -> Path:
        return cls.department_pilot_dir(workspace_id, department_id) / "audit.jsonl"
