from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class DailyStory(BaseModel):
    date: str = Field(description="ISO date string YYYY-MM-DD")
    headline: str = Field(
        description="A short, evocative 1-sentence headline capturing the theme of the day"
    )
    wins: List[str] = Field(
        description="2 to 4 concrete accomplishments, finished tasks, or handled challenges"
    )
    friction_and_delays: List[str] = Field(
        description="2 to 3 postponed tasks, cognitive blocks, or derailments"
    )
    narrative: str = Field(
        description="The human, empathetic story of how the day actually unfolded (2 tight paragraphs, max 150 words total, honest tone)"
    )
    tomorrow_pivot: str = Field(
        description="One grounded, specific tactical adjustment for tomorrow morning"
    )
    cognitive_pattern: str = Field(
        description="Summary of energy/clarity shifts across the day"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )