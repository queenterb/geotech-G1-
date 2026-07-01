from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, JSON, String, Text

from app.db.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(128), nullable=False)
    severity = Column(String(32), nullable=False)
    source = Column(String(128), nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    description = Column(Text, nullable=True)
