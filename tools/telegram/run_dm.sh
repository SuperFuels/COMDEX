#!/usr/bin/env bash
set -euo pipefail
cd /workspaces/COMDEX

export TG_API_ID="31202789"
export TG_API_HASH="ba0e05d01079a4af64cc9e836d839018"
export TG_SESSION="data/telegram/gip0101"

export TG_DM_IN="data/telegram/users.txt"
export TG_DM_LOG="data/telegram/dm_log.json"

export TG_DM_MAX="${TG_DM_MAX:-10}"
export TG_DM_SLEEP="${TG_DM_SLEEP:-12}"
export TG_DM_SEND_LINKS="${TG_DM_SEND_LINKS:-0}"

export TG_DM_GIF="/workspaces/COMDEX/frontend/public/images/GIP_repo_animated.gif"

python tools/telegram/dm_gip_card.py
