# CONNECTIVITY

## Repro (C01)

```bash
cd /workspaces/COMDEX
env PYTHONPATH=$PWD/CONNECTIVITY/src python -m pytest \
  CONNECTIVITY/tests/programmable_connectivity/test_c01_shortcut_routing.py -q

Artifacts land in:
	•	CONNECTIVITY/artifacts/programmable_connectivity/C01/<run_hash>/