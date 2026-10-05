from typing import Optional, Literal
from pydantic import BaseModel, Field


class VoiceDisruptionIntent(BaseModel):
    is_schedule_disruption: bool = Field(
        description="True if the user mentions missing an event, running late, oversleeping, or needing a replan."
    )
    disruption_type: Optional[Literal["missed_event", "overslept", "delay_traffic", "cancel_plan", "general_pivot"]] = Field(
        default=None,
        description="Category of the disruption."
    )
    missed_event_description: Optional[str] = Field(
        default=None,
        description="Brief description of what was missed or delayed (e.g., '1:30 study block', 'morning gym')."
    )
    urgency: Literal["low", "medium", "high"] = "medium"