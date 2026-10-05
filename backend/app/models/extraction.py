from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ExtractedTask(BaseModel):
    title: str = Field(
        description="Concise, imperative task title (e.g., 'Review PR #42', 'Send proposal to Rahul')."
    )
    is_professional: bool = Field(
        description="True if related to work, projects, engineering, or official business."
    )
    commitment_type: Literal["self_promise", "explicit_approval", "direct_mention_urgent"] = Field(
        description="Proof of commitment: 'self_promise' (user said they will do it), 'explicit_approval' (user said 'ok', 'on it', 'in'), or 'direct_mention_urgent' (@user tagged for deliverable)."
    )
    estimated_minutes: int = Field(
        ge=2, le=240,
        description="Realistic duration in minutes. Quick checks/links = 2-5 min; short emails/replies = 5-10 min; deep tasks = 30-90 min. Do NOT pad small tasks into 15-30 min."
    )
    deadline: Optional[str] = Field(
        default=None,
        description="ISO datetime or null if no explicit time commitment was made."
    )
    priority: Literal["low", "medium", "high", "critical"] = "medium"


class ObservationTriageResult(BaseModel):
    actionable: bool = Field(
        description="False if the message is casual banter, open question without approval, domestic noise, or a status update requiring no work."
    )
    rejection_reason: Optional[str] = Field(
        default=None,
        description="Why this was discarded (e.g., 'unconfirmed question', 'casual domestic talk', 'no explicit user commitment')."
    )
    task: Optional[ExtractedTask] = Field(
        default=None,
        description="Populated ONLY if actionable is True and user confirmed/promised or was strictly tagged."
    )