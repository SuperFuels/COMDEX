#!/bin/zsh
set -euo pipefail

project_dir="${0:A:h:h}"
source "${0:A:h}/resolve-unity.zsh"

mkdir -p "$project_dir/Logs"

# The Apple-silicon editor bundles the package server as an Intel helper. On
# newer macOS releases Unity can time out while launching that helper itself,
# so keep it alive under this build shell and hand Unity its IPC channel.
unity_app="${unity_bin:h:h}"
upm_bin="$unity_app/Resources/PackageManager/Server/UnityPackageManager"
upm_parent_pid=$$
upm_name="Upm-$upm_parent_pid"
upm_path="/tmp/Unity-$upm_name.sock"
"$upm_bin" -s "$upm_parent_pid" -ipc -ipc-path "$upm_path" -l 2 &
upm_pid=$!
trap 'kill "$upm_pid" 2>/dev/null || true' EXIT
# Rosetta may need a few seconds to translate the Intel helper on first run.
sleep 20

"$unity_bin" \
  -batchmode \
  -nographics \
  -quit \
  -projectPath "$project_dir" \
  -upmIpcPath "$upm_name" \
  -executeMethod Tessaris.SpatialBoardroom.Editor.SpatialBoardroomProjectSetup.BuildWebForBatch \
  -logFile "$project_dir/Logs/build-web.log"

print "Built: $project_dir/Builds/WebGL"
