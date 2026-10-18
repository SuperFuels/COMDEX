#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.modules.aion_business.runtime.business_vault_coverage_migration import (
    BusinessVaultCoverageMigration,
)
from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
)
from backend.modules.aion_business.runtime.guardian_business_container_repository import (
    GuardianBusinessContainerRepository,
)
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Dry-run or copy/verify all known Tessaris business-data surfaces "
            "into the configured external Business Vault."
        )
    )
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--actor", default="business-vault-migration-operator")
    parser.add_argument(
        "--legacy-root",
        type=Path,
        default=AIONBusinessPaths.ROOT,
        help="Legacy AION Business root. Defaults to the current runtime root.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Copy and verify. Omit for the non-mutating dry run.",
    )
    parser.add_argument(
        "--local-node-root",
        type=Path,
        default=Path(".runtime/local_node"),
        help=(
            "Legacy Local Node root containing workflow diagrams, approvals "
            "and workflow audit logs."
        ),
    )
    parser.add_argument(
        "--workflow-capsule-root",
        type=Path,
        default=Path(".runtime/workflow_capsules"),
        help=(
            "Legacy Workflow Capsule root. Customer-authored 'my' glyphs are "
            "migrated; signed universal product templates and the derived "
            "index are excluded."
        ),
    )
    parser.add_argument(
        "--aion-learning-root",
        type=Path,
        default=Path(".runtime/COMDEX_MOVE/data"),
        help=(
            "Retained AION teaching, learning and prediction data root. "
            "Sources are copied and verified; they are never deleted."
        ),
    )
    parser.add_argument(
        "--aion-resonance-root",
        type=Path,
        default=Path("backend/state"),
        help=(
            "Retained AION Φ/resonance state root. Sources are copied and "
            "verified; they are never deleted."
        ),
    )
    parser.add_argument(
        "--aion-resonance-data-root",
        type=Path,
        default=Path("data"),
        help=(
            "Retained application-relative AION resonance/conversation data "
            "root. Sources are copied and verified; they are never deleted."
        ),
    )
    parser.add_argument(
        "--pal-snapshot-log",
        type=Path,
        default=Path("data/analysis/pal_snapshots.jsonl"),
        help=(
            "Retained PAL snapshot JSONL source. Records are copied and "
            "verified; the source is never deleted."
        ),
    )
    parser.add_argument(
        "--glyphnet-thread-db",
        type=Path,
        default=Path("data/threadlog.sqlite"),
        help=(
            "Retained GlyphNet thread SQLite source. Messages are copied and "
            "verified; the source is never deleted."
        ),
    )
    parser.add_argument(
        "--aion-knowledge-db",
        type=Path,
        default=Path("data/knowledge/aion_knowledge_graph.db"),
        help=(
            "Retained AION knowledge-graph SQLite source. Triplets are copied "
            "and verified; the source is never deleted."
        ),
    )
    parser.add_argument(
        "--concept-reinforcement-log",
        type=Path,
        default=Path("data/feedback/concept_reinforcement.log"),
        help="Retained concept reinforcement source; copied without deletion.",
    )
    parser.add_argument(
        "--concept-evolution-log",
        type=Path,
        default=Path("data/feedback/concept_evolution_snapshot.jsonl"),
        help="Retained concept evolution source; copied without deletion.",
    )
    parser.add_argument(
        "--aion-flow-model-bindings",
        type=Path,
        default=Path("data/aion_flow/credential_bindings/model-bindings.json"),
        help=(
            "Retained model-binding metadata. Opaque credential locators are "
            "copied into Guardian while secrets stay in their encrypted store."
        ),
    )
    args = parser.parse_args()

    runtime = configured_business_vault_runtime()
    migration = BusinessVaultCoverageMigration(
        legacy_root=args.legacy_root,
        local_node_root=args.local_node_root,
        workflow_capsule_root=args.workflow_capsule_root,
        aion_learning_root=args.aion_learning_root,
        aion_resonance_root=args.aion_resonance_root,
        aion_resonance_data_root=args.aion_resonance_data_root,
        pal_snapshot_log_path=args.pal_snapshot_log,
        aion_knowledge_db_path=args.aion_knowledge_db,
        concept_reinforcement_log_path=args.concept_reinforcement_log,
        concept_evolution_log_path=args.concept_evolution_log,
        glyphnet_thread_db_path=args.glyphnet_thread_db,
        aion_flow_model_bindings_path=args.aion_flow_model_bindings,
        domain_store=VaultDomainStore(
            runtime.guardian,
            actor_id=args.actor,
        ),
        object_store=runtime.objects,
        guardian_containers=GuardianBusinessContainerRepository(
            runtime.guardian,
            default_actor_id=args.actor,
        ),
    )
    report = migration.migrate_workspace(
        args.workspace,
        actor_id=args.actor,
        execute=args.execute,
    )
    # The report contains identifiers, states and counts only; it never prints
    # business payloads, source file contents, secrets or encryption material.
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if (not args.execute or report["authority_switch_allowed"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
