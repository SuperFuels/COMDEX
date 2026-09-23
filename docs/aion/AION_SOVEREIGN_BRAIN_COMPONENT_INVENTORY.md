# AION Sovereign Brain — Existing Component Inventory

Status: Phase 0 implementation inventory — 3 September 2026

This inventory prevents the Sovereign Business Brain and AION Flow work from duplicating systems
already present in COMDEX. It classifies components by the treatment required to place them behind
the frozen sovereign-brain boundary.

## Reuse directly

| Capability | Existing component | Decision |
|---|---|---|
| Deterministic/local model routing | `backend/modules/aion/runtime/services/model_router.py` | Reuse behind the unified route contract. |
| Visual workflow compilation | `backend/modules/workflow_capsules/canvas/canvas_workflow_compiler.py` | Reuse after sovereign preflight validation. |
| Workflow execution | `backend/modules/workflow_capsules/execution/workflow_capsule_runner.py` | Reuse; execution remains separate from drawing or compiling. |
| Permission evaluation | `backend/modules/workflow_capsules/permissions/permission_evaluator.py` | Reuse as an execution gate. |
| Provider response parsing | `backend/modules/workflow_capsules/architect/provider_adapter.py` | Reuse; provider output remains untrusted input. |
| Workflow graph review | `backend/modules/workflow_capsules/architect/graph_compiler.py` | Reuse after AION Flow validation. |
| Business repositories | `backend/modules/aion_business/runtime/*_repository.py` | Reuse as customer-controlled stores. |
| Pilot surfaces | `backend/modules/aion_fabric` and `backend/modules/pilot_unified` | Reuse as governed presentation/control surfaces. |
| Workflow Architect UI | `frontend/src/glyphnet/components/workflow-architect` | Reuse as the first AION Flow authoring surface. |

## Adapt behind a versioned contract

| Area | Required adaptation |
|---|---|
| Model/provider adapters | Declare identity, model version, location, residency, permitted data classes, cost and health. |
| Canvas nodes and edges | Add disclosure, encryption, authority, budget and verification metadata. |
| Route receipts | Normalize provider-neutral request/result hashes and avoid unnecessary prompt retention. |
| Business graph | Add source, confidence, visibility and review state to every inferred relation. |
| Provider fallback | Prohibit crossing privacy, residency or cost boundaries without a newly authorized route. |
| Learning | Learn route/outcome performance without allowing a provider to write canonical customer truth. |

## Retire or prohibit

- Provider-specific canonical memory or provider-owned business-map records.
- Any model adapter able to grant authority, approve its own action or erase receipts.
- Hidden fallback from local/private processing to an external provider.
- Infinite or open-ended model debate loops.
- Treating agreement between models as evidence.
- Direct execution from an unvalidated canvas edge or raw model tool call.
- Credential, prompt or private-result storage inside portable route receipts.

## New Phase 0 components

- `contracts/sovereign_brain.py` publishes provider-independent brain, export, business-map and route-receipt contracts.
- `runtime/sovereign_flow_compiler.py` encloses visual intelligence graphs inside AION admission and receipt boundaries.
- The Pilot `/brain` page explains the ownership and deployment model publicly without requiring sign-in.
