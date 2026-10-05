from datetime import datetime, timezone
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class UserStateVector(BaseModel):
    # Continuous dimensions (1-10)
    physical_alertness: int = Field(
        ge=1, le=10,
        description="1 = half-asleep/exhausted, 10 = fully awake/caffeinated"
    )
    cognitive_clarity: int = Field(
        ge=1, le=10,
        description="1 = severe brain fog/decision fatigue, 10 = laser focus/sharp working memory"
    )
    drive_vs_friction: int = Field(
        ge=1, le=10,
        description="1 = high resistance/dread/anxiety, 10 = eager/motivated/high momentum"
    )

    # Inferred operational archetype
    operating_mode: Literal[
        "deep_flow",
        "restless_scattered",
        "cognitive_depletion",
        "friction_locked",
        "passive_absorption",
        "steady_neutral"
    ] = Field(description="The primary operational state governing what type of work fits best")

    trigger_evidence: List[str] = Field(
        default_factory=list,
        description="Specific phrases or contextual clues from the voice text justifying this state"
    )
    coaching_summary: str = Field(
        description="Grounded 1-sentence assessment of the user's current capacity"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))