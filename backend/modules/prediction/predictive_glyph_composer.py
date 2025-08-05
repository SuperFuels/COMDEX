import asyncio
from typing import Dict, List
from backend.modules.knowledge_graph.glyph_formatter import format_prediction_for_ghx

# ✅ Lazy loader to break circular import with PredictionEngine
def get_prediction_engine():
    from backend.modules.consciousness.prediction_engine import PredictionEngine
    return PredictionEngine

# ✅ Lazy loader to break circular import with glyphnet_ws
def get_broadcast_event():
    from backend.routes.ws.glyphnet_ws import broadcast_event
    return broadcast_event


class PredictiveGlyphComposer:
    def __init__(self, container_id: str):
        self.container_id = container_id
        PredictionEngineClass = get_prediction_engine()
        self.engine = PredictionEngineClass(container_id=container_id)

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

        ghx_payload = [format_prediction_for_ghx(p) for p in predictions]

        # 🔮 Lazy import for broadcast_event to avoid circular import
        broadcast_event = get_broadcast_event()
        await broadcast_event(
            event="predictive_forks",
            payload={"container_id": self.container_id, "forks": ghx_payload}
        )
        return predictions

    async def validate_fork(self, fork_id: str, accept: bool):
        """Agent validation feedback for a fork: accept (commit to KG) or prune (discard)."""
        if accept:
            print(f"✅ Fork accepted: {fork_id}")
            # Could inject fork into Codex/KG here
        else:
            print(f"🗑️ Fork pruned: {fork_id}")
            await self.engine.gradient_engine._inject_gradient_feedback(
                {"id": fork_id}, "Pruned predictive fork"
            )