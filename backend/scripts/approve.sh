#!/bin/bash
# approve.sh — CLI wrapper for approving DNA proposals

if [ -z "$1" ]; then
  echo "❌ Usage: ./approve.sh <proposal_id>"
  exit 1
fi

if [ -z "$AION_MASTER_KEY" ]; then
  echo "❌ Please set the AION_MASTER_KEY environment variable."
  exit 1
fi

PYTHONPATH=. python backend/modules/dna_chain/approve_proposal.py "$1" "$AION_MASTER_KEY"