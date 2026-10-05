from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field


class RawObservation(BaseModel):
    source: Literal["email", "chat", "audio", "manual"]
    channel: str = "Gmail"
    sender: str
    raw_text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    processed: bool = False
    processed_at: Optional[datetime] = None
    extracted_type: Optional[str] = None