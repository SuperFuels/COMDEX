#!/usr/bin/env python3
import os
import sys

# make sure your venv is activated and your PYTHONPATH is set so
# that “backend.utils.auth” is importable.
from backend.utils.auth import verify_password

# Paste in the hash you retrieved:
stored_hash = "$2b$12$........................................"

# And the plaintext you think you used:
candidate   = "the_plaintext_password_you_used"

print("Does it match?", verify_password(candidate, stored_hash))
