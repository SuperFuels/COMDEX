backend/modules/dna_chain/dna_registry.py
# ✅ DNA Registry — Canonical list of registered AION files
# This file is updated by DNA_SWITCH and used for auditing and mutation tracking

DNA_REGISTRY = {
    "backend/modules/aion/sample_agent.py": {
        "type": "agent",
        "dna_id": "agent.sample_agent",
        "registered": True,
        "last_modified": "2025-07-06T14:32:00Z",
        "switch": True,
    },
    "backend/modules/hexcore/state_manager.py": {
        "type": "core_module",
        "dna_id": "core.state_manager",
        "registered": True,
        "last_modified": "2025-07-06T13:47:00Z",
        "switch": True,
    },
    "frontend/components/AIONDashboardClient.tsx": {
        "type": "frontend_ui",
        "dna_id": "ui.dashboard_client",
        "registered": True,
        "last_modified": "2025-07-06T15:10:00Z",
        "switch": True,
    },
}