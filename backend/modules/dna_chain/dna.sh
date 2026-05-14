#!/bin/bash

# dna.sh
# Usage:
#   ./dna.sh write <file> <old> <new> <reason>
#   ./dna.sh approve <proposal_id>

if [ "$1" = "write" ]; then
  PYTHONPATH=. python backend/modules/dna_chain/dna_writer.py \
    --file "$2" \
    --replaced "$3" \
    --new "$4" \
    --reason "$5"
elif [ "$1" = "approve" ]; then
  AION_MASTER_KEY=your-key-here \
  PYTHONPATH=. python backend/modules/dna_chain/approve_proposal.py "$2"
else
  echo "Usage:"
  echo "  ./dna.sh write <file> <old> <new> <reason>"
  echo "  ./dna.sh approve <proposal_id>"
fi
