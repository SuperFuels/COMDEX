from __future__ import annotations

from backend.modules.aion_business.contracts.containers import ContainerBindingSpec
from backend.modules.aion_business.contracts.topology import BusinessTopology
from backend.modules.aion_business.contracts.workspace import WorkspaceSpec
from backend.modules.aion_business.contracts.agents import AgentSpec
from backend.modules.aion_business.contracts.roles import RoleSpec
from backend.modules.aion_business.contracts.tasks import LearningRecord, TaskRecord
from backend.modules.aion_business.runtime.agent_repository import AgentRepository
from backend.modules.aion_business.runtime.learning_repository import LearningRepository
from backend.modules.aion_business.runtime.role_repository import RoleRepository
from backend.modules.aion_business.runtime.task_record_repository import TaskRecordRepository
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.container_binding_repository import ContainerBindingRepository
from backend.modules.aion_business.runtime.department_operational_store import DepartmentOperationalStore
from backend.modules.aion_business.runtime.topology_repository import TopologyRepository
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_business.runtime.workspace_repository import WorkspaceRepository


def test_workspace_bindings_and_topology_restart_from_encrypted_vault(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"c" * 32)
    operational = DepartmentOperationalStore(domain_store=VaultDomainStore(guardian))
    workspaces = WorkspaceRepository(operational_store=operational)
    bindings = ContainerBindingRepository(operational_store=operational)
    topologies = TopologyRepository(operational_store=operational)

    workspaces.save(WorkspaceSpec(
        id="acme", name="Private Workspace", business_type="services", owner="private-founder",
    ))
    bindings.save(ContainerBindingSpec(
        id="customers", workspace_id="acme", name="Private Customers",
        runtime_container_id="container-private",
    ))
    topologies.save(BusinessTopology(workspace_id="acme"))

    assert WorkspaceRepository(operational_store=operational).load("acme").name == "Private Workspace"
    assert ContainerBindingRepository(operational_store=operational).load("acme", "customers").name == "Private Customers"
    assert TopologyRepository(operational_store=operational).load("acme").workspace_id == "acme"
    assert workspaces.list_ids() == ["acme"]
    assert bindings.list_workspace_ids() == ["acme"]
    assert b"Private Workspace" not in guardian.database.read_bytes()
    assert b"Private Customers" not in guardian.database.read_bytes()

    assert bindings.delete("acme", "customers") is True
    assert bindings.load_optional("acme", "customers") is None
    assert topologies.delete("acme") is True
    assert topologies.load_optional("acme") is None


def test_agent_role_task_and_learning_records_restart_from_encrypted_vault(tmp_path):
    layout = provision_business_vault(
        tmp_path / "vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "app", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"r" * 32)
    operational = DepartmentOperationalStore(domain_store=VaultDomainStore(guardian))
    agents = AgentRepository(operational_store=operational)
    roles = RoleRepository(operational_store=operational)
    tasks = TaskRecordRepository(operational_store=operational)
    learning = LearningRepository(operational_store=operational)

    agents.save(AgentSpec(
        id="agent-private", workspace_id="acme", agent_type="persistent_role",
        role="Operations", business_type="services", objective="Private objective",
    ))
    roles.save(RoleSpec(
        id="role-private", workspace_id="acme", role_type="CUSTOM",
        business_type="services", objective_set=["Private objective"],
    ))
    tasks.save(TaskRecord(
        id="task-private", workspace_id="acme", created_by="private-founder",
        owned_by_role="role-private", objective="Private task",
    ))
    learning.save(LearningRecord(
        id="learning-private", source_type="task", source_id="task-private",
        business_area="operations", signal_type="success", summary="Private learning",
    ), "acme")

    assert AgentRepository(operational_store=operational).load("acme", "agent-private").objective == "Private objective"
    assert RoleRepository(operational_store=operational).load("acme", "role-private").objective_set == ["Private objective"]
    assert TaskRecordRepository(operational_store=operational).list_for_role("acme", "role-private")[0].objective == "Private task"
    assert LearningRepository(operational_store=operational).load("acme", "learning-private").summary == "Private learning"
    plaintext = guardian.database.read_bytes()
    for value in (b"Private objective", b"Private task", b"Private learning"):
        assert value not in plaintext
