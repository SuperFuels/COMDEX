# 📄 backend/modules/symbolic/mutation_trigger.py

from backend.modules.symbolic.mutation_engine import mutate_container_logic

def trigger_mutation_if_needed(collapse: float, decoherence: float, container_id: str):
    """
    Triggers a symbolic mutation if collapse is too low or decoherence is too high.
    Uses the main mutation engine to update container glyphs.
    """
    if collapse < 0.5 or decoherence > 0.4:
        print(f"[⚠️] Triggering mutation on container {container_id} due to collapse={collapse:.2f}, decoherence={decoherence:.2f}")
        mutate_container_logic(container_id=container_id, reason="decoherence spike")