# THERMO

## Repro (X01)

```bash
cd /workspaces/COMDEX
env PYTHONPATH=$PWD/THERMO/src python -m pytest \
  THERMO/tests/programmable_thermo/test_x01_entropic_recycling.py -vv

Artifacts land in:
	•	THERMO/artifacts/programmable_thermo/X01/<run_hash>/

    