# backend/models/fork.py

"""
🧬 Fork Model
------------------------
Represents a symbolic fork in a wave execution path,
created during CodexLang mutation or SQI divergence.
Used in collapse trace logs and innovation tracking.
"""

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base  # SQLAlchemy declarative base

class Fork(Base):
    __tablename__ = "forks"

    # Primary Key
    id = Column(String, primary_key=True, index=True)

    # Wave/Beam relationship
    parent_wave_id = Column(String, index=True)  # ID of the parent wave this fork originated from
    linked_beam_id = Column(String, nullable=True)  # Optional: track originating beam

    # Metrics
    sqi_score = Column(Float, nullable=True)  # Symbolic Quality Index of the fork
    innovation_score = Column(Float, nullable=True)  # Optional: creative novelty score
    mutation_type = Column(String, nullable=True)  # e.g., 'logical', 'goal_shift', 'conceptual'

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    creator_id = Column(String, nullable=True)  # Optional: user or agent responsible
    source_context = Column(Text, nullable=True)  # Optional: raw context for trace

    # Optional relationships
    # beam = relationship("Beam", back_populates="forks")  # If a Beam model exists

    def __repr__(self):
        return f"<Fork(id={self.id}, parent_wave_id={self.parent_wave_id}, sqi_score={self.sqi_score})>"