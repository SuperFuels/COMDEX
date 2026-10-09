#!/bin/zsh
set -euo pipefail
setopt null_glob

source "${0:A:h}/resolve-unity.zsh"

license_dir="${TESSARIS_UNITY_LICENSE_DIR:-$HOME/Library/Unity/TessarisLicensing}"
mkdir -p "$license_dir"
license_files=("$license_dir"/*.ulf)

if (( ${#license_files[@]} == 0 )); then
  print -u2 "No .ulf response file was found in $license_dir"
  print -u2 "Upload Unity_v6000.0.79f1.alf on Unity's manual activation page, then save the downloaded .ulf file in that folder."
  exit 1
fi

"$unity_bin" -batchmode -quit -manualLicenseFile "${license_files[-1]}" \
  -logFile "$license_dir/activation.log"

print "Unity licence applied. You can now run build-macos.command."
