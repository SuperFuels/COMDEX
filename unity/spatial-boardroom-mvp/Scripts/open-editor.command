#!/bin/zsh
set -euo pipefail

project_dir="${0:A:h:h}"
source "${0:A:h}/resolve-unity.zsh"

open -a "$unity_app" --args -projectPath "$project_dir"
