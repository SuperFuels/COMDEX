#!/bin/zsh
set -euo pipefail

project_dir="${0:A:h:h}"
source "${0:A:h}/resolve-unity.zsh"

mkdir -p "$project_dir/Logs"

"$unity_bin" \
  -batchmode \
  -nographics \
  -quit \
  -projectPath "$project_dir" \
  -executeMethod Tessaris.SpatialBoardroom.Editor.SpatialBoardroomProjectSetup.BuildForBatch \
  -logFile "$project_dir/Logs/build-macos.log"

print "Built: $project_dir/Builds/macOS/Tessaris Spatial Boardroom.app"
