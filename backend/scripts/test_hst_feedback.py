import asyncio
import time
from backend.modules.holograms.hst_generator import HSTGenerator
from backend.modules.holograms.hst_field_analyzer import HSTFieldAnalyzer


async def main():
    # Initialize HST generator session
    hst = HSTGenerator()
    print(f"🧠 Initialized HST Session → {hst.session_id}")

    # Broadcast initial state (forces feedback + coherence updates)
    for i in range(5):
        hst.broadcast_state(force=True)
        await asyncio.sleep(0.2)

    # Instantiate the analyzer with the correct session_id
    analyzer = HSTFieldAnalyzer(session_id=hst.session_id)
    summary = analyzer.summarize_field()
    print("\n📊 Final Analyzer Summary:")
    print(summary)


if __name__ == "__main__":
    asyncio.run(main())