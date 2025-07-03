from sqlalchemy import Column, Integer, String, Text, DateTime, func
from backend.database import Base  # import the shared Base from your database.py

class DreamRecord(Base):
    __tablename__ = "dream_records"

    id = Column(Integer, primary_key=True, index=True)
    dream_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    source = Column(String(100), default="dream_core", nullable=False)

    def __repr__(self):
        return f"<DreamRecord(id={self.id}, created_at={self.created_at})>"