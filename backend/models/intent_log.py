# File: backend/models/intent_log.py

from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from backend.database import Base

class IntentLog(Base):
    __tablename__ = "intent_logs"

    id = Column(Integer, primary_key=True, index=True)
    intent_type = Column(String, nullable=False)
    data = Column(Text, nullable=False)
    outcome = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)