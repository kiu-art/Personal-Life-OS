from datetime import datetime, timezone
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class Task(BaseModel):
    title: str
    description: Optional[str] = None
    entity: Optional[str] = None
    source_observation_id: Optional[str] = None
    status: Literal["pending", "in_progress", "completed", "dismissed"] = "pending"
    deadline: Optional[datetime] = None
    estimated_minutes: int = 45
    actual_minutes_logged: int = 0
    elasticity: Literal["fixed", "flexible", "liquid"] = "flexible"
    energy_required: Literal["high", "medium", "low"] = "medium"
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))