from datetime import datetime, time
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# Individual block on today's timeline
class TimeBlock(BaseModel):
    start_time: str = Field(description="Start time in HH:MM format (e.g. '10:30')")
    end_time: str = Field(description="End time in HH:MM format (e.g. '11:15')")
    title: str = Field(description="Concise activity title")
    block_type: Literal["fixed_anchor", "deep_work", "quick_task", "routine", "recharge", "buffer"] = Field(
        description="Category of the block"
    )
    task_id: Optional[str] = Field(default=None, description="Linked MongoDB task _id if applicable")
    action_notes: str = Field(description="Concrete advice on what to focus on during this block")
    status_tag: Literal["intact", "compressed", "rescheduled", "new"] = Field(
        default="intact",
        description="What the secretary did to this block relative to the ideal plan"
    )


# Structured response from local LLM
class DynamicDayPlan(BaseModel):
    summary_verdict: str = Field(
        description="Secretary's quick situational diagnosis (e.g. 'Overslept by 2.5 hours. Dropped low-priority chores and compressed deep work to protect your 2 PM meeting.')"
    )
    schedule: List[TimeBlock] = Field(description="Chronological sequence of blocks from right now until bedtime")
    deferred_tasks: List[str] = Field(
        default_factory=list,
        description="Tasks deliberately moved off today's plate to prevent overload"
    )
    vital_warnings: List[str] = Field(
        default_factory=list,
        description="Crucial deadlines or non-negotiables that must not slip today"
    )


# Request DTO when asking for a replan
class ReplanRequest(BaseModel):
    current_time: Optional[str] = Field(default=None, description="HH:MM format")
    situation_note: Optional[str] = Field(default="Routine dynamic replan request", description="Reason for replanning")
    hard_stop_bedtime: Optional[str] = Field(default="23:30", description="HH:MM cutoff")
    target_date: Optional[str] = Field(default=None, description="YYYY-MM-DD format (defaults to today)")