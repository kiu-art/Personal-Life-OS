from datetime import datetime, timezone
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class MemoryFact(BaseModel):
    category: str = Field(
        default="general",
        description="Category: 'people', 'preferences', 'patterns', 'goals', 'health', 'work'",
    )
    subject: str = Field(
        description="Entity or topic the memory belongs to (e.g., 'Ayush', 'Rahul', 'Gym')",
    )
    predicate: str = Field(
        default="observed_fact",
        description="Relationship or property (e.g., 'prefers_workout_time', 'project_partner')",
    )
    object: str = Field(
        description="The core statement, value, or fact",
    )
    summary: str = Field(
        description="Human-readable explanation of this memory",
    )
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="Extraction confidence score",
    )
    source_event: Optional[str] = Field(
        default=None,
        description="Traceability tag (e.g., 'whatsapp_6ac2b48e', 'voice_checkin')",
    )
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class MemoryFactResponse(BaseModel):
    id: str
    category: str
    subject: str
    predicate: str
    object: str
    summary: str
    confidence: float
    source_event: Optional[str] = None
    tags: List[str]
    created_at: datetime


class CategorizedMemoryResponse(BaseModel):
    total_facts: int
    categories: dict[str, List[MemoryFactResponse]]