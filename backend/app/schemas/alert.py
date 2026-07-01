from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, Optional


class AlertCreate(BaseModel):
    event_type: str
    severity: str
    source: str
    payload: Dict[str, Any]
    description: Optional[str] = None


class AlertRead(AlertCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
