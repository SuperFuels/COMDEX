# backend/modules/symbolic/metrics_hooks.py

def log_sqi_drift(container_id: str, beam_id: str, glow: float, frequency: float):
    print(f"[SQI] Drift beam {beam_id} in {container_id} → glow={glow:.4f}, pulse={frequency:.2f}Hz")

def log_collapse_metric(container_id: str, beam_id: str, score: float, state: str):
    print(f"[CodexMetric] Beam {beam_id} in {container_id} → SQI={score:.4f}, state={state}")