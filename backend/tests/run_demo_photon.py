# backend/tests/run_demo_photon.py

from backend.modules.photonlang.importer import install
install()  # enable .photon imports

import sys
sys.path.insert(0, "/workspaces/COMDEX/backend/tests")  # <-- demo_math.photon lives here

import demo_math  # loads backend/tests/demo_math.photon transparently

out = demo_math.add_and_measure(2, 3)
print("OK", out)