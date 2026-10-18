#!/usr/bin/env bash
set -euo pipefail

TIER="${1:?usage: run_tier_lock_ladder.sh TIER SEED_START CASES BANK_BITS TARGET_COVERAGE}"
SEED_START="${2:?usage: run_tier_lock_ladder.sh TIER SEED_START CASES BANK_BITS TARGET_COVERAGE}"
CASES="${3:?usage: run_tier_lock_ladder.sh TIER SEED_START CASES BANK_BITS TARGET_COVERAGE}"
BANK_BITS="${4:?usage: run_tier_lock_ladder.sh TIER SEED_START CASES BANK_BITS TARGET_COVERAGE}"
TARGET_COVERAGE="${5:?usage: run_tier_lock_ladder.sh TIER SEED_START CASES BANK_BITS TARGET_COVERAGE}"

BEAM_COUNT="${BEAM_COUNT:-10}"
SEEDS_PER_BEAM="${SEEDS_PER_BEAM:-1}"
MAX_STEPS="${MAX_STEPS:-5000000}"
PREFER="${PREFER:-pollard}"

OUT_DIR="benchmarks/sqi_semiprime_lab/tier_transfer"

echo "=== SQI tier lock benchmark-only ladder ==="
echo "tier=$TIER"
echo "seed_start=$SEED_START"
echo "cases=$CASES"
echo "bank_bits=$BANK_BITS"
echo "target_coverage=$TARGET_COVERAGE"
echo

BANK_COUNT="$(PYTHONPATH=. python backend/modules/sqi/factor/semiprime_prior_bank_lab.py rank \
  --bits "$BANK_BITS" \
  --method pollard \
  --limit 999999 | tr ',' '\n' | sed '/^$/d' | wc -l | tr -d ' ')"

if [ "$BANK_COUNT" -lt 1 ]; then
  echo "ERROR: no native priors found for bank_bits=$BANK_BITS"
  exit 1
fi

OUT_SUFFIX="coverage_${TIER}_bank${BANK_COUNT}_pollard_cases${CASES}"

echo "=== benchmark: $OUT_SUFFIX ==="

PYTHONPATH=. python backend/modules/sqi/factor/tier_transfer_benchmark.py \
  --tiers "$TIER" \
  --cases "$CASES" \
  --seed-start "$SEED_START" \
  --prefer "$PREFER" \
  --beam-count "$BEAM_COUNT" \
  --seeds-per-beam "$SEEDS_PER_BEAM" \
  --max-steps "$MAX_STEPS" \
  --prior-bits "$BANK_BITS" \
  --prior-limit "$BANK_COUNT" \
  --out-suffix "$OUT_SUFFIX"

REPORT="$OUT_DIR/tier_transfer_${OUT_SUFFIX}.json"

echo
echo "=== coverage summary ==="
PYTHONPATH=. python - "$REPORT" "$TARGET_COVERAGE" <<'PY'
import json, sys
from pathlib import Path

report = Path(sys.argv[1])
target = int(sys.argv[2])
r = json.loads(report.read_text())

case_count = r.get("case_count")
verified_count = r.get("verified_count")

print(f"report={report}")
print(f"coverage={verified_count}/{case_count}")

if verified_count >= target:
    print("LOCKED: target coverage reached.")
    raise SystemExit(0)

for row in r["rows"]:
    if not row.get("verified"):
        t = row["target"]
        print()
        print("NEXT_FAILED_CASE")
        print(f"seed={t.get('seed')}")
        print(f"N={t.get('n')}")
        print(f"P={t.get('p')}")
        print(f"Q={t.get('q')}")
        print()
        print("Manual discovery command:")
        print(f'N={t.get("n")}')
        print()
        print("PYTHONPATH=. python backend/modules/sqi/factor/semiprime_prior_discovery_lab.py \"$N\" \\")
        print("  --prefer pollard \\")
        print("  --seed-start 1 \\")
        print("  --seed-end 80 \\")
        print("  --c-start 1 \\")
        print("  --c-end 512 \\")
        print("  --max-steps 300000 \\")
        print("  --workers 8 \\")
        print("  --chunk-size 16 \\")
        print("  --progress-every 50 \\")
        print("  --save-partial \\")
        print(f"  --out-suffix discover_{t.get('seed')}_quick \\")
        print("  --add-to-bank \\")
        print(f"  --bank-bits {r.get('prior_bits')} \\")
        print(f"  --bank-source manual_quick_{t.get('seed')} \\")
        print("  --json")
        break
PY
