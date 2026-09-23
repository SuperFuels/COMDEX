#!/bin/zsh
set -euo pipefail
setopt null_glob

unity_bin="/Volumes/Install macOS Sonoma/Tessaris/Unity/Editors/6000.0.79f1/Unity/Unity.app/Contents/MacOS/Unity"
license_dir="/Volumes/Install macOS Sonoma/Tessaris/Unity/Licensing"
license_files=("$license_dir"/*.ulf)

if [[ ! -x "$unity_bin" ]]; then
  print -u2 "Connect the Tessaris SD card before activating Unity."
  exit 1
fi

if (( ${#license_files[@]} == 0 )); then
  print -u2 "No .ulf response file was found in $license_dir"
  print -u2 "Upload Unity_v6000.0.79f1.alf on Unity's manual activation page, then save the downloaded .ulf file in that folder."
  exit 1
fi

"$unity_bin" -batchmode -quit -manualLicenseFile "${license_files[-1]}" \
  -logFile "$license_dir/activation.log"

print "Unity licence applied. You can now run build-macos.command."
