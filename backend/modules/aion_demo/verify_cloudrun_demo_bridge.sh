#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   CLOUD_RUN_URL="https://<your-service-xxxxx-uc.a.run.app>" ./verify_cloudrun_demo_bridge.sh
#
# Optional:
#   PREFIX="/aion-demo" (default)
#   PREFIX=""           (if you mounted the bridge at root)

: "${CLOUD_RUN_URL:?Set CLOUD_RUN_URL=https://<cloudrun-host>}"
PREFIX="${PREFIX:-/aion-demo}"

BASE="${CLOUD_RUN_URL%/}${PREFIX}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "== AION Demo Bridge Cloud Run Sweep =="
echo "Base: $BASE"
echo

req() {
  local method="$1"
  local path="$2"
  local name="$3"

  local url="${BASE}${path}"
  local out="${TMP}/resp.json"
  local code

  echo "-- $name: $method $url"
  code="$(curl -sS -o "$out" -w "%{http_code}" -X "$method" "$url" \
    -H "Content-Type: application/json")" || {
      echo "   ✗ curl failed"
      exit 1
    }

  if [[ "$code" != "200" ]]; then
    echo "   ✗ HTTP $code"
    echo "   Body:"
    sed -n '1,200p' "$out" || true
    exit 1
  fi

  # Validate JSON + print a compact summary (no jq needed)
  python3 - "$name" < "$out" <<'PY'
import json, sys
name = sys.argv[1]
raw = sys.stdin.read().strip()
try:
  j = json.loads(raw) if raw else {}
except Exception as e:
  print(f"   ✗ invalid JSON: {e}")
  sys.exit(1)

def pick(d, path):
  cur = d
  for p in path.split("."):
    if not isinstance(cur, dict) or p not in cur:
      return None
    cur = cur[p]
  return cur

ok = j.get("ok")
action = j.get("action")
svc = j.get("service")
phi_pulse = pick(j, "phi.derived.metabolic_pulse") or pick(j, "derived.metabolic_pulse")
adr_status = pick(j, "adr.derived.adr_status") or pick(j, "derived.adr_status")

bits = []
if ok is not None: bits.append(f"ok={ok}")
if action: bits.append(f"action={action}")
if svc: bits.append(f"service={svc}")
if phi_pulse: bits.append(f"phi_pulse={phi_pulse}")
if adr_status: bits.append(f"adr_status={adr_status}")

print("   ✓ " + (", ".join(bits) if bits else "json_ok"))
PY

  echo
}

# --- Core reads ---
req GET  "/health"  "health"
req GET  "/api/phi" "phi_state"
req GET  "/api/adr" "adr_state"

# --- Demo actions (the on-stage buttons) ---
req POST "/api/demo/phi/reset"         "phi_reset"
req POST "/api/demo/phi/inject_entropy" "phi_inject_entropy"
req POST "/api/demo/phi/recover"        "phi_recover"
req POST "/api/demo/adr/inject"         "adr_inject"
req POST "/api/demo/adr/run"            "adr_run"

echo "✅ Cloud Run sweep passed."
echo
echo "Optional WS check (requires websocat):"
echo "  websocat -n1 \"${BASE/https:/wss:}/ws/aion-demo\""