# ✅ backend/modules/glyphwave/utils/fork_lookup.py

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from backend.database import get_db  # <- uses your existing database.py
from backend.models.fork import Fork

def get_forks_by_wave_id(wave_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve symbolic wave forks associated with a given wave_id from the database.
    Each fork represents a collapsed variant or symbolic mutation.
    """
    db: Session = next(get_db())
    forks = (
        db.query(Fork)
        .filter(Fork.parent_wave_id == wave_id)
        .all()
    )
    return [
        {
            "id": fork.id,
            "sqi_score": fork.sqi_score,
        }
        for fork in forks
    ]