#!/bin/zsh

# Keep the project usable whether the exact Unity editor is installed locally
# or carried on the original Tessaris development volume.
unity_candidates=(
  "/Applications/Unity/Unity.app"
  "$HOME/Applications/Unity/Unity.app"
  "/Applications/Unity/Hub/Editor/6000.0.79f1/Unity.app"
  "$HOME/Applications/Unity/Hub/Editor/6000.0.79f1/Unity.app"
  "/Volumes/Install macOS Sonoma/Tessaris/Unity/Editors/6000.0.79f1/Unity/Unity.app"
)

for unity_candidate in "${unity_candidates[@]}"; do
  if [[ -d "$unity_candidate" ]]; then
    unity_app="$unity_candidate"
    unity_bin="$unity_candidate/Contents/MacOS/Unity"
    return 0
  fi
done

print -u2 "Unity 6000.0.79f1 was not found. Install that exact editor version before opening or building Spatial Boardroom."
return 1
