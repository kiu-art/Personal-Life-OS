from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class WeeklyBehavioralPattern(BaseModel):
    pattern_title: str = Field(
        description="Short summary of the observed habit/tendency (e.g., 'Early Meeting Drag', 'Caffeine Crash Loop')"
    )
    trigger: str = Field(
        description="The recurring condition (e.g., 'First meeting scheduled before 10:00 AM')"
    )
    observed_outcome: str = Field(
        description="What consistently happened as a result (e.g., 'Postponed analytical coding by an average of 4 hours')"
    )
    frequency_days: int = Field(
        ge=1, le=7,
        description="Number of days this dynamic played out over the past week"
    )


class WeeklyReview(BaseModel):
    week_start_date: str = Field(description="YYYY-MM-DD")
    week_end_date: str = Field(description="YYYY-MM-DD")
    headline: str = Field(
        description="A sharp, evocative title capturing the macro theme of the week"
    )
    narrative_reflection: str = Field(
        description="2 tight paragraphs reflecting on the week's trajectory, energy, and execution (authentic, candid tone)"
    )
    key_wins: List[str] = Field(
        description="Top 3-5 major milestones completed across the 7 days"
    )
    persistent_frictions: List[str] = Field(
        description="2-4 recurring blockers, delayed tasks, or friction states"
    )
    behavioral_patterns: List[WeeklyBehavioralPattern] = Field(
        description="1 to 3 cross-day cause-and-effect patterns extracted from the week"
    )
    tactical_directive_next_week: str = Field(
        description="One concrete, enforceable schedule adjustment for next week (e.g., 'Protect 8:30-10:30 AM on Tuesday/Thursday for deep work')"
    )
    dominant_operating_mode: str = Field(
        description="The primary cognitive mode of the week (e.g., 'steady_neutral', 'friction_locked', 'deep_flow')"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )