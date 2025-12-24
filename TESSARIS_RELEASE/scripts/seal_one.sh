#!/usr/bin/env bash
set -euo pipefail

PAPER_ID="${1:-}"
if [[ -z "$PAPER_ID" ]]; then
  echo "Usage: scripts/seal_one.sh <PAPER_ID>"
  exit 1
fi

echo "Sealing (stub): $PAPER_ID"
echo "TODO: run repro command, write artifact to runs/, sha256sum, update registry row, mark SEALED."
