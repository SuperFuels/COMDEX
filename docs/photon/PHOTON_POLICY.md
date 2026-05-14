Photon Policy & Safety

This page documents the Tessaris Photon importer’s safety controls,
how to lock down imports, and which glyph/token spaces are reserved.

It covers:
	•	Import-time policy (environment variables)
	•	Signature / integrity checks
	•	Reserved glyph & token rules
	•	CI recipes, examples, and troubleshooting

⸻

1) Import-time Policy (Environment Variables)

Env var
Type
Default
Example
Effect
PHOTON_TB
bool (1/0)
0
PHOTON_TB=1
Enable Photon-aware traceback enrichment (maps exceptions back to original .photon lines).
PHOTON_IMPORT_BYPASS
bool (1/0)
0
PHOTON_IMPORT_BYPASS=1
Skip Photon expansion and execute raw source (debug only).
PHOTON_HOST_DENY
csv modules
(empty)
PHOTON_HOST_DENY=os,subprocess
Block these host Python modules from being imported by .photon code. On violation: ImportError.
PHOTON_HOST_ALLOW
csv prefixes
(empty)
PHOTON_HOST_ALLOW=backend,photon_runtime
Optional allow-list of module name prefixes that .photon code may import. If set, anything not matching one of the prefixes is rejected.
PHOTON_SIG_SHA256
hex digest
(unset)
`PHOTON_SIG_SHA256=$(sha256sum m.photon
cut -d’ ’ -f1)`
PHOTON_POLICY_STRICT
bool (1/0)
1 (recommended)
PHOTON_POLICY_STRICT=1
Treat any policy violation as fatal. Set 0 only for local debugging.


Precedence & order
	1.	On importing X.photon, the importer: reads raw file → runs policy checks
(HOST_DENY, HOST_ALLOW, SIG_SHA256) → expands Photon→Python →
executes. If PHOTON_IMPORT_BYPASS=1, expansion is skipped.
	2.	If both PHOTON_HOST_ALLOW and PHOTON_HOST_DENY are set, deny wins.
	3.	PHOTON_POLICY_STRICT=1 is recommended for CI and prod.

⸻

2) Signature / Integrity

What is checked?
If PHOTON_SIG_SHA256 is set, the importer hashes the raw .photon file and
requires an exact match.

Compute a digest

# macOS/Linux (GNU coreutils)
sha256sum path/to/module.photon | cut -d' ' -f1

# Python (portable)
python - <<'PY'
import hashlib, sys
print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())
PY path/to/module.photon

Typical uses
	•	Lock a known-good artifact in CI or a reproducible release.
	•	Pair with PHOTON_HOST_DENY to restrict host surface.

⸻

3) Reserved Glyphs / Token Space
	•	The canonical keyword/operator/punctuation mapping lives in
python_token_map.json (rendered in
docs/photon/token_table.md).
	•	Curly braces { and } are never compressed on the Python→Photon path
to avoid collisions with f-string/format braces.
	•	Future-reserved:
	•	Embedded signature blocks (e.g., ed25519) in .photon
	•	Multi-file package manifests for Photon modules

⸻

4) Examples

Block dangerous hosts

export PHOTON_HOST_DENY="os,subprocess"
python -m backend.modules.photonlang.cli run backend/tests/demo_math.photon -e 'add_and_measure(2,3)'

Enforce a specific artifact

export PHOTON_SIG_SHA256=$(sha256sum backend/tests/demo_math.photon | awk '{print $1}')
python -m backend.modules.photonlang.cli run backend/tests/demo_math.photon -e 'add_and_measure(2,3)'

Allow-list only your packages

export PHOTON_HOST_ALLOW="backend,photon_runtime"
python -m backend.modules.photonlang.cli run your_module.photon

Photon-aware tracebacks

PHOTON_TB=1 python -m backend.modules.photonlang.cli run backend/tests/demo_error.photon -e 'oops(3)'

Bypass expansion (debug only)

PHOTON_IMPORT_BYPASS=1 python -m backend.modules.photonlang.cli run your_module.photon

5) CI “strict” recipe

export PHOTON_TB=1
export PHOTON_POLICY_STRICT=1
export PHOTON_HOST_DENY=os,subprocess
# optionally pin an artifact:
# export PHOTON_SIG_SHA256=...

pytest -q

6) Troubleshooting

Symptom
Likely cause
Fix
ImportError: SHA256 mismatch ... (policy)
PHOTON_SIG_SHA256 doesn’t match raw file bytes
Recompute with `sha256sum file.photon
ImportError: host import 'os' denied by policy
Import blocked by PHOTON_HOST_DENY
Remove the import or adjust policy; deny takes precedence over allow.
Code runs but tracebacks show Python lines, not Photon
PHOTON_TB disabled
Set PHOTON_TB=1.
Behavior differs between local and CI
Different policy envs
Print/export the env in CI logs; align PHOTON_* vars across environments.


See also:
	•	Token table: docs/photon/token_table.md
	•	CLI usage: python -m backend.modules.photonlang.cli -h


