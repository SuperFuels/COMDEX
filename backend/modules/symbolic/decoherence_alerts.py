# backend/modules/symbolic/decoherence_alerts.py

from backend.modules.sqi.metrics_bus import metrics_bus

DECOHERENCE_THRESHOLD = 0.4  # Customize

def check_anomaly(decoherence_rate: float, container_id: str):
    if decoherence_rate > DECOHERENCE_THRESHOLD:
        alert = {
            "type": "decoherence_alert",
            "container_id": container_id,
            "severity": "high",
            "value": decoherence_rate,
        }
        metrics_bus.push(alert)