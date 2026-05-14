# Phase 3 Ops Runbook — Governed Learning Influence and LLM Weighting

## Scope

Operational runbook for Phase 3 governance controls covering:

- Decision influence runtime audit review
- LLM weighting accuracy log review
- Safe dry-run update/revert workflows
- Live-apply auth guard usage
- Recovery via rollback/revert to target version
- Post-rollback verification checklist

---

## 1. Files and Runtime Artifacts

### Decision influence runtime artifacts
- **Weights JSON (persisted state):** `.runtime/COMDEX_MOVE/data/trading/decision_influence_weights.json`
- **Audit JSONL (governance trail):** `.runtime/COMDEX_MOVE/data/trading/decision_influence_audit.jsonl`

### LLM weighting runtime artifacts
- **Accuracy log JSONL:** `.runtime/COMDEX_MOVE/data/trading/llm_accuracy_log.jsonl`

---

## 2. Review Decision Influence Audit Trail

### What to inspect
Audit entries are JSONL rows and should include (where applicable):

- `action` (`update`, `revert`, `rollback`)
- `dry_run`
- `changed`
- `weights_version_before`
- `weights_version_after`
- `rejected_count`
- `runtime_error` (if any)
- `pre_snapshot` / `post_snapshot` (for governed updates and revert/rollback paths)
- `target` / `target_snapshot` (for revert/rollback)

### Quick CLI checks

#### Latest audit rows
```bash
tail -n 20 .runtime/COMDEX_MOVE/data/trading/decision_influence_audit.jsonl