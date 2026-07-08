# AION Voice Python Runtime Staging

This folder is the target location for the future packaged voice runtime.

Current O23E status:
- The directory contract exists.
- The staging launcher delegates to the proven local .venv_voice/bin/python.
- The real release build must replace this launcher with an embedded or relocatable Python 3.12 runtime.
- .venv_voice/ must not be committed directly.

Expected final packaged path:
Tessaris.app/Contents/Resources/voice/python/bin/python
