# TUNNEL

## Repro (TN01)

```bash
cd /workspaces/COMDEX
env PYTHONPATH=$PWD/TUNNEL/src python -m pytest TUNNEL/tests/programmable_tunnel/test_tn01_transmission_lock.py -q

Artifacts land in:
	•	TUNNEL/artifacts/programmable_tunnel/TN01/<run_hash>/
---
