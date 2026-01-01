#!/usr/bin/env bash
set -Eeuo pipefail

trap 'echo "FAIL line=$LINENO cmd=$BASH_COMMAND" >&2' ERR

cd /workspaces/COMDEX || exit 1
export PYTHONPATH=.
OUT="backend/modules/knowledge"

json_get() {
  local key="$1"
  local file="$2"
  python - <<PY
import json
with open("${file}","r",encoding="utf-8") as f:
    j=json.load(f)
v=j.get("${key}","")
print("" if v is None else v)
PY
}

lock_bundle () {
  local NAME="$1"
  local ROOT="$2"
  local TEST="$3"
  local JSON_SRC="$4"
  shift 4
  local EXTRA_FILES=("$@")

  echo "=== RUN ${NAME} ==="
  python "backend/photon_algebra/tests/${TEST}" | tee "/tmp/${NAME}_latest.log"

  local RUN_ID GIT_REV TS
  RUN_ID="$(json_get run_id "${JSON_SRC}")"
  GIT_REV="$(json_get git_rev "${JSON_SRC}")"
  TS="$(json_get timestamp "${JSON_SRC}")"

  [[ -n "${RUN_ID}" && "${RUN_ID}" != "None" ]] || { echo "bad run_id in ${JSON_SRC}" >&2; return 1; }

  local RUN_DIR="${ROOT}/runs/${RUN_ID}"
  mkdir -p "${ROOT}"/{runs,checksums,logs,tests,docs} "${RUN_DIR}"

  cp -f "backend/photon_algebra/tests/${TEST}" "${ROOT}/tests/${TEST}"
  cp -f "${JSON_SRC}" "${RUN_DIR}/$(basename "${JSON_SRC}")"

  for f in "${EXTRA_FILES[@]}"; do
    [[ -f "${OUT}/${f}" ]] || { echo "missing: ${OUT}/${f}" >&2; return 1; }
    cp -f "${OUT}/${f}" "${RUN_DIR}/"
  done

  printf "%s\n" "${GIT_REV}" > "${RUN_DIR}/GIT_REV.txt"
  printf "%s\n" "${GIT_REV}" > "${ROOT}/GIT_REV.txt"
  printf "%s\n" "${RUN_ID}"  > "${ROOT}/runs/LATEST_RUN_ID.txt"

  cp -f "/tmp/${NAME}_latest.log" "${ROOT}/logs/${RUN_ID}.log"

  if [[ ! -f "${ROOT}/AUDIT_REGISTRY.md" ]]; then
    printf "# %s Audit Registry (v0.4)\n\n" "${NAME}" > "${ROOT}/AUDIT_REGISTRY.md"
  fi
  {
    echo "- RUN_ID: ${RUN_ID}"
    echo "  GIT_REV: ${GIT_REV}"
    echo "  Timestamp (JSON): ${TS}"
  } >> "${ROOT}/AUDIT_REGISTRY.md"

  cat > "${ROOT}/docs/${NAME}_EVIDENCE_BLOCK.md" <<EOF
# ${NAME} Evidence Block (v0.4)

RUN_ID: ${RUN_ID}
GIT_REV: ${GIT_REV}

Pinned test:
- docs/Artifacts/v0.4/${NAME}/tests/${TEST}

Pinned JSON:
- docs/Artifacts/v0.4/${NAME}/runs/${RUN_ID}/$(basename "${JSON_SRC}")

Pinned plots:
$(for f in "${EXTRA_FILES[@]}"; do echo "- docs/Artifacts/v0.4/${NAME}/runs/${RUN_ID}/$(basename "$f")"; done)

Pinned log:
- docs/Artifacts/v0.4/${NAME}/logs/${RUN_ID}.log
EOF

  cat > "${ROOT}/ARTIFACTS_INDEX.md" <<EOF
# ${NAME} Artifacts Index (v0.4)

RUN_ID: ${RUN_ID}
GIT_REV: ${GIT_REV}

Run folder:
- docs/Artifacts/v0.4/${NAME}/runs/${RUN_ID}/

Pinned artifacts:
- runs/${RUN_ID}/$(basename "${JSON_SRC}")
$(for f in "${EXTRA_FILES[@]}"; do echo "- runs/${RUN_ID}/$(basename "$f")"; done)
- runs/${RUN_ID}/GIT_REV.txt

Pinned test + logs:
- tests/${TEST}
- logs/${RUN_ID}.log

Evidence/Audit:
- docs/${NAME}_EVIDENCE_BLOCK.md
- AUDIT_REGISTRY.md

Anchors:
- GIT_REV.txt
- runs/LATEST_RUN_ID.txt

Checksums:
- checksums/${RUN_ID}.sha256
- ARTIFACTS_INDEX.sha256
EOF

  local SHA="${ROOT}/checksums/${RUN_ID}.sha256"
  (
    cd "${ROOT}" || exit 1
    sha256sum \
      AUDIT_REGISTRY.md \
      "docs/${NAME}_EVIDENCE_BLOCK.md" \
      ARTIFACTS_INDEX.md \
      GIT_REV.txt \
      runs/LATEST_RUN_ID.txt \
      "tests/${TEST}" \
      "logs/${RUN_ID}.log" \
      "runs/${RUN_ID}/GIT_REV.txt" \
      "runs/${RUN_ID}/$(basename "${JSON_SRC}")" \
      $(for f in "${EXTRA_FILES[@]}"; do echo "runs/${RUN_ID}/$(basename "$f")"; done) \
      > "checksums/${RUN_ID}.sha256"
  )

  ( cd "${ROOT}" && sha256sum -c "checksums/${RUN_ID}.sha256" )

  (
    cd "${ROOT}" || exit 1
    sha256sum ARTIFACTS_INDEX.md GIT_REV.txt runs/LATEST_RUN_ID.txt > ARTIFACTS_INDEX.sha256
  )
  ( cd "${ROOT}" && sha256sum -c ARTIFACTS_INDEX.sha256 )

  echo "=== LOCKED ${NAME} === RUN_ID=${RUN_ID}"
}

# P7A (note: NEW demod plot name)
lock_bundle "P7A" "docs/Artifacts/v0.4/P7A" \
  "paev_test_P7_loom_broadcast_modulation.py" \
  "backend/modules/knowledge/P7A_loom_broadcast_modulation.json" \
  "PAEV_P7A_Loom_DemodCorrQ_vs_Distance.png"

lock_bundle "P7B" "docs/Artifacts/v0.4/P7B" \
  "paev_test_P7_link_nonlocal_coupling.py" \
  "backend/modules/knowledge/P7B_link_nonlocal_coupling.json" \
  "PAEV_P7B_Link_ResponseMag_vs_k.png" \
  "PAEV_P7B_Link_Lag_vs_k.png"

lock_bundle "P8" "docs/Artifacts/v0.4/P8" \
  "paev_test_P8_syntax_multiplexer.py" \
  "backend/modules/knowledge/P8_syntax_multiplexer.json" \
  "PAEV_P8_Multiplexer_Delta_vs_Distance.png" \
  "PAEV_P8_Multiplexer_RhoB_vs_Distance.png" \
  "PAEV_P8_Multiplexer_RhoC_vs_Distance.png"
