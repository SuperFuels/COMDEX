# backend/start.py

import os
import uvicorn

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# import the FastAPI instance from main.py
from main import app

if __name__ == "__main__":
    # Cloud Run will inject PORT; default to 8080 for local dev
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(
        app,                 # use the imported FastAPI app
        host="0.0.0.0",
        port=port,
        reload=True,         # hot reload in local dev
        log_level="info"
    )

