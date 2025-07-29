import asyncio
from typing import Dict, List
from backend.modules.prediction.prediction_engine import PredictionEngine
from backend.modules.glyphnet.glyphnet_ws import broadcast_event  # WebSocket broadcast
from backend.modules.knowledge_graph.glyph_formatter import format_prediction_for_ghx

class PredictiveGlyphComposer:
    def __init__(self, container_id: str):
        self.container_id = container_id
        self.engine = PredictionEngine(container_id=container_id)

    async def compose_forward_forks(
        self,
        current_glyph: str,
        goal: str = None,
        coord: str = None,
        emotion: str = None,
        num_paths: int = 3,
        agent_id: str = "local"
    ) -> List[Dict]:
        """Generate forward glyph forks (predictive) and broadcast to GHX viewer."""
        predictions = await self.engine.generate_future_paths(
            current_glyph=current_glyph,
            goal=goal,
            coord=coord,
            emotion=emotion,
            num_paths=num_paths,
            agent_id=agent_id
        )

        ghx_payload = []
        for p in predictions:
            ghx_payload.append(format_prediction_for_ghx(p))

        # 🔮 Broadcast ghost links to GHX Viewer UI
        await broadcast_event(
            event="predictive_forks",
            payload={"container_id": self.container_id, "forks": ghx_payload}
        )
        return predictions

    async def validate_fork(self, fork_id: str, accept: bool):
        """Agent validation feedback for a fork: accept (commit to KG) or prune (discard)."""
        if accept:
            print(f"✅ Fork accepted: {fork_id}")
            # Here we could inject fork into Codex/KG as committed glyph path
        else:
            print(f"🗑️ Fork pruned: {fork_id}")
            # Optionally trigger gradient feedback for pruning
            await self.engine.gradient_engine._inject_gradient_feedback(
                {"id": fork_id}, "Pruned predictive fork"
            )