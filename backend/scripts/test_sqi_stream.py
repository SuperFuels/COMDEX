# File: scripts/test_sqi_stream.py
import asyncio
import time
from backend.modules.glyphwave.telemetry_handler import TelemetryHandler

async def main():
    handler = TelemetryHandler()
    await handler.connect()
    print("\n🌐 Starting continuous SQI telemetry stream (10 seconds)...\n")
    start = time.time()

    async for metrics in handler.stream_metrics(interval=1.0):
        print(f"[{time.strftime('%H:%M:%S')}] "
              f"coh={metrics.get('coherence_stability', 0):.3f} | "
              f"Δφ={metrics.get('phase_drift', 0):.3f} | "
              f"H={metrics.get('entropy', 0):.3f} | "
              f"Vis={metrics.get('visibility', 0):.3f} | "
              f"pSQI={metrics.get('pattern_sqi', 0):.3f}")
        if time.time() - start > 10:
            break

    await handler.disconnect()
    print("\n✅ Stream completed and telemetry disconnected.\n")

if __name__ == "__main__":
    asyncio.run(main())