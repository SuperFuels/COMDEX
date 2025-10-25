"""
🌐 Photon Runtime API Endpoint
------------------------------
Simple REST-style interface to trigger Photon execution.
Used by CodexCore and Aion web clients.
"""

from fastapi import FastAPI, UploadFile
from backend.modules.wiki_capsules.photon_runtime.photon_executor_extension import run_photon_file

app = FastAPI(title="Tessaris Photon Runtime API")


@app.post("/codex/run-photon")
async def run_photon_endpoint(file: UploadFile):
    """Accepts a .phn or .ptn file and executes it."""
    tmp_path = f"/tmp/{file.filename}"
    with open(tmp_path, "wb") as f:
        f.write(await file.read())
    result = run_photon_file(tmp_path)
    return result