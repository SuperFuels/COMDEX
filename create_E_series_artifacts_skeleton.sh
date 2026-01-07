#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-docs/Artifacts/v0.4/E}"

mkdir -p \
  "${ROOT}/checksums" \
  "${ROOT}/docs" \
  "${ROOT}/logs" \
  "${ROOT}/runs" \
  "${ROOT}/scenes" \
  "${ROOT}/tests"

# Record git rev if available (else placeholder).
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git rev-parse HEAD > "${ROOT}/GIT_REV.txt"
else
  echo "<GIT_REV_UNKNOWN>" > "${ROOT}/GIT_REV.txt"
fi

# Minimal index + audit registry placeholders (you'll overwrite with the blocks below).
cat > "${ROOT}/ARTIFACTS_INDEX.md" <<'MD'
# Artifacts Index — v0.4 / E-Series (E1–E6h)

This directory contains locked artifacts for the Tessaris E-Series (universality / cross-constant robustness).

- Series: E (E1–E6h)
- Repo: <REPO_NAME>
- Commit: see `GIT_REV.txt`
- Run ID: <RUN_ID_UTC>
- Status: STAGED

## Runs
- `runs/<RUN_ID_UTC>/` — stdout logs, JSON evidence, plots

## Checksums
- `checksums/SHA256SUMS.txt` — sha256 for `runs/<RUN_ID_UTC>/` contents

MD

cat > "${ROOT}/AUDIT_REGISTRY.md" <<'MD'
# Audit Registry — v0.4 / E-Series

## Entry
- Lock ID: E-00-E1--E6h
- Status: STAGED
- Run ID: <RUN_ID_UTC>
- Commit: (see `GIT_REV.txt`)
- Evidence: `runs/<RUN_ID_UTC>/` + `checksums/SHA256SUMS.txt`

MD

# Create a deterministic index checksum placeholder (regenerate after edits)
( cd "${ROOT}" && sha256sum ARTIFACTS_INDEX.md > ARTIFACTS_INDEX.sha256 ) || true

echo "OK: created ${ROOT}"
