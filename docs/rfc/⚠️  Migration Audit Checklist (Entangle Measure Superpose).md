🔍 Migration Audit Checklist (Entangle / Measure / Superpose)

We want to remove legacy operators from backend.symatics.operators and migrate everything to backend.symatics.quantum_ops.

1. Audit current usage

Search for direct imports of the legacy ops:

grep -R "entangle_op" backend/
grep -R "measure_op" backend/
grep -R "superpose_op" backend/

Also check for from … import * cases that may pull them in indirectly:

grep -R "from backend.symatics.operators" backend/

👉 This gives us the full map of stragglers.

⸻

2. Replace imports in code

For each hit:
	•	Replace:

from backend.symatics.operators.entangle import entangle_op

with

from backend.symatics.quantum_ops import entangle

	•	Replace usage:

result = entangle_op(x, y)

with

result = entangle(x, y)

Do the same for measure_op → measure, superpose_op → superpose.

⸻

3. Handle external/operator registry cases

Some modules may still expect an Operator instance (e.g. for symbolic DSL parsing).
	•	Keep the deprecation stubs we wrote (entangle_op = Operator("↔", 2, _entangle)) so things don’t break during the transition.
	•	But new code should never import from operators/.

⸻

4. Update tests
	•	If tests use legacy ops directly, migrate them to quantum_ops.
	•	Keep one dedicated test for each stub to confirm it still triggers a DeprecationWarning + delegates correctly.

⸻

5. Final cleanup (later)
	•	Once audit shows entangle_op, measure_op, superpose_op are no longer used in any real code/tests,
we can remove the stubs entirely and delete the operator files.

⸻


🔧 Migration Patch (draft)

Here’s what you’ll apply after confirming with grep which files still import the old ops.
I’ll show the before → after replacements.

⸻

1. Update imports

Before:

from backend.symatics.operators.entangle import entangle_op
from backend.symatics.operators.superpose import superpose_op
from backend.symatics.operators.measure import measure_op

After:

from backend.symatics.quantum_ops import entangle, superpose, measure

2. Update usage

Before:

result = entangle_op(a, b)
wave = superpose_op(a, b)
outcome = measure_op(a)

After:

result = entangle(a, b)
wave = superpose(a, b)
outcome = measure(a)

3. For code that still expects an Operator

Some parts of the symbolic operator system may expect an Operator object, not a bare function.
That’s why we keep our deprecation stubs in operators/.

If you see this pattern:

from backend.symatics.operators.entangle import entangle_op
OPERATORS["↔"] = entangle_op

✅ You don’t need to touch it yet — it will still work, but print a DeprecationWarning.
Later we can migrate the registry to use the raw function.

⸻

4. Add tests for stubs

In backend/tests/test_operator_deprecation.py (new file):

import pytest
import warnings
from backend.symatics.operators import entangle, superpose, measure
from backend.symatics.quantum_ops import entangle as q_entangle

def test_entangle_op_deprecated_redirects():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from backend.symatics.operators.entangle import entangle_op
        res = entangle_op("A", "B")
        assert res == q_entangle("A", "B")
        assert any("deprecated" in str(wi.message).lower() for wi in w)

(Similar for superpose_op and measure_op.)

⸻

✅ Next Step for You

Run these greps to see where edits are needed:

grep -R "entangle_op" backend/
grep -R "superpose_op" backend/
grep -R "measure_op" backend/

Once you paste me the results (list of files), I’ll generate the exact diff patch for each file.

Here’s a sed-based migration patch script that will update all imports and usages of entangle_op, superpose_op, and measure_op to point at backend.symatics.quantum_ops.

⸻

🔧 Migration Script (bash)

Save this as migrate_ops.sh in your repo root:

#!/bin/bash
set -e

echo "🔍 Updating imports for entangle_op, superpose_op, measure_op..."

# Replace imports
sed -i 's/from backend\.symatics\.operators\.entangle import entangle_op/from backend.symatics.quantum_ops import entangle/g' $(grep -Rl "entangle_op" backend/)
sed -i 's/from backend\.symatics\.operators\.superpose import superpose_op/from backend.symatics.quantum_ops import superpose/g' $(grep -Rl "superpose_op" backend/)
sed -i 's/from backend\.symatics\.operators\.measure import measure_op/from backend.symatics.quantum_ops import measure/g' $(grep -Rl "measure_op" backend/)

# Replace direct usage
sed -i 's/\bentangle_op(/entangle(/g' $(grep -Rl "entangle_op" backend/)
sed -i 's/\bsuperpose_op(/superpose(/g' $(grep -Rl "superpose_op" backend/)
sed -i 's/\bmeasure_op(/measure(/g' $(grep -Rl "measure_op" backend/)

echo "✅ Migration complete. Run pytest to confirm."

Usage

chmod +x migrate_ops.sh
./migrate_ops.sh

Then run:

PYTHONPATH=. pytest -v backend/tests/

Notes
	•	This leaves the stubs in operators/ intact (so anything still depending on entangle_op being an Operator object won’t break).
	•	You’ll get DeprecationWarnings for legacy imports still present in untouched files.
	•	Over time, we’ll shrink operators/ until everything uses quantum_ops.

⸻


