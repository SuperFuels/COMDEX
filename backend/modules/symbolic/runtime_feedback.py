# backend/modules/symbolic/runtime_feedback.py

import httpx

async def send_runtime_feedback(collapse: float, decoherence: float, container_id: str = "default"):
    try:
        payload = {
            "name": "collapse_feedback",
            "container_id": container_id,
            "data": {
                "collapse_per_sec": collapse,
                "decoherence_rate": decoherence
            }
        }
        async with httpx.AsyncClient() as client:
            await client.post("http://localhost:8000/sqi/kernel/physics/ingest", json=payload)
    except Exception as e:
        print(f"[⚠️] Feedback send failed: {e}")