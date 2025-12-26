# Tessaris Terminal (Phase0)

Tools:
- validate_artifacts_contract.py  (already in repo)
- index_artifacts.py
- export_snapshot.py

Examples:

```bash
# validate
python Tessaris_OS/TERMINAL/tools/validate_artifacts_contract.py MATTER/artifacts
python Tessaris_OS/TERMINAL/tools/validate_artifacts_contract.py BRIDGE/artifacts

# index
env PYTHONPATH=$PWD/Tessaris_OS/TERMINAL/src python \
  Tessaris_OS/TERMINAL/tools/index_artifacts.py MATTER/artifacts

# export reviewer snapshot
env PYTHONPATH=$PWD/Tessaris_OS/TERMINAL/src python \
  Tessaris_OS/TERMINAL/tools/export_snapshot.py MATTER/artifacts/programmable_matter/MT02/20ba5f5
