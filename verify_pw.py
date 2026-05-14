#!/usr/bin/env python3
importos
importsys

# ✅ DNA Switch
frombackend.modules.dna.dna_switchimportDNA_SWITCH
DNA_SWITCH.register(__file__)# Allow tracking + upgrades to this file

# make sure your venv is activated and your PYTHONPATH is set so
# that "backend.utils.auth" is importable.
frombackend.utils.authimportverify_password

# Paste in the hash you retrieved:
stored_hash="$2b$12$........................................"

# And the plaintext you think you used:
candidate="the_plaintext_password_you_used"

print("Does it match?",verify_password(candidate,stored_hash))
