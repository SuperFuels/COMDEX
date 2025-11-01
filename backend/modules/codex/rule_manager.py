# -*- coding: utf-8 -*-
from __future__ import annotations
import asyncio
import httpx
from typing import Dict, Any

class RuleManager:
    def __init__(self):
        self.weights: Dict[str, float] = {}
        self.last_drift: Dict[str, Any] = {}

    async def pull_sqi_drift(self):
        """
        Periodically poll the SQI Drift API and update rule weights.
        """
        url = "http://localhost:8000/api/sqi/drift/list"
        async with httpx.AsyncClient() as client:
            while True:
                try:
                    resp = await client.get(url, timeout=3)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data and isinstance(data, dict):
                            self.last_drift = data
                            self._adapt_from_drift(data)
                except Exception as e:
                    print(f"[CFE] SQI drift poll failed: {e}")
                await asyncio.sleep(5)  # poll every 5 seconds

    def _adapt_from_drift(self, drift: Dict[str, Any]):
        coherence = drift.get("meta", {}).get("coherence", 1.0)
        total_weight = drift.get("total_weight", 1.0)
        entropy_shift = drift.get("meta", {}).get("entropy_drift", 0.0)

        # Adapt symbolic rule weights based on drift magnitude
        self.weights["⊕"] = round(1.0 - entropy_shift, 4)
        self.weights["μ"] = round(coherence, 4)
        self.weights["↔"] = round(total_weight / (1 + abs(entropy_shift)), 4)

        print(f"[CFE] Updated rule weights -> {self.weights}")