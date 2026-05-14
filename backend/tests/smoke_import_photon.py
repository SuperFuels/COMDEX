from backend.photonlang.importer import install
install()

# Make sure import path includes ./examples
import sys, os
examples = os.path.abspath("examples")
if examples not in sys.path:
    sys.path.insert(0, examples)

import demo_math  # loads examples/demo_math.photon transparently

out = demo_math.add_and_measure(2, 3)
print("OK", out)