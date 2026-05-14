# MAGNETISM

## Repro (MG01)

```bash
cd /workspaces/COMDEX
env PYTHONPATH=$PWD/MAGNETISM/src python -m pytest MAGNETISM/tests/programmable_magnetism/test_mg01_curl_control.py -q
```

Artifacts land in:
- MAGNETISM/artifacts/programmable_magnetism/MG01/<run_hash>/
