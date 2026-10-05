from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

from pydantic import BaseModel, Field
from app.core.database import get_database
from app.services.state_extractor import state_engine
from app.models.user_state import UserStateVector

from app.core.database import get_database
from app.services.state_extractor import state_engine
from app.models.user_state import UserStateVector

class TaskRecommendation(BaseModel):
    task_id: str = Field(description="The exact _id of the recommended task.")
    title: str = Field(description="Task title.")
    tactical_action: str = Field(
        description="What the user should ACTUALLY do during this exact block."
    )
    why_now: str = Field(
        description="Reasoning linking deadlines, task weight, and cognitive state."
    )
    is_chunked: bool = Field(
        default=False,
        description="True if the task is too large for this state/window and requires a small entry step.",
    )

class AIRecommendationDecision(BaseModel):
    user_state_snapshot: UserStateVector
    primary_recommendation: TaskRecommendation
    alternative_recommendations: List[TaskRecommendation] = []
    coaching_note: str


router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


def time_to_minutes(t_str: Optional[str]) -> int:
    if not t_str or not isinstance(t_str, str):
        return 0
    parts = t_str.strip().split(":")
    if len(parts) < 2:
        return 0
    return int(parts[0]) * 60 + int(parts[1])


@router.get("/what-next", response_model=AIRecommendationDecision)
async def get_what_next(
    available_minutes: int = Query(default=45, description="Available focus minutes"),
    notes: Optional[str] = Query(default="", description="Additional contextual notes"),
):
    """
    Tactical recommendation engine (WSIDN - What Should I Do Now?).
    Examines active schedule blocks, cognitive capacity, and pending/scheduled tasks.
    """
    db = get_database()
    now = datetime.now()
    now_hm = now.strftime("%H:%M")
    current_mins = time_to_minutes(now_hm)
    today_str = now.strftime("%Y-%m-%d")

    # 1. Fetch current cognitive state vector safely
    try:
        user_state = await state_engine.get_latest_state()
    except Exception:
        user_state = None

    if not user_state:
        user_state = UserStateVector(
            physical_alertness=7,
            cognitive_clarity=7,
            drive_vs_friction=7,
            operating_mode="steady_neutral",
            coaching_summary="Nominal operating baseline.",
            trigger_evidence=[],
            timestamp=datetime.now(timezone.utc),
        )

    # 2. Query Candidate Tasks: Include both 'pending' AND 'scheduled'
    cursor = db.tasks.find({
        "completed": {"$ne": True},
        "status": {"$in": ["pending", "scheduled", "in_progress", None]},
    }).sort("deadline", 1).limit(10)
    candidate_tasks = await cursor.to_list(length=10)

    # 3. Check if today's active schedule block links directly to a task
    target_task = None
    active_block_title = None

    sched_doc = await db.schedules.find_one({"date": today_str})
    if sched_doc:
        raw_blocks = sched_doc.get("blocks") or sched_doc.get("schedule") or []
        for b in raw_blocks:
            s_mins = time_to_minutes(b.get("start_time"))
            e_mins = time_to_minutes(b.get("end_time"))
            if s_mins <= current_mins <= e_mins:
                active_block_title = b.get("title")
                tid = b.get("task_id")
                if tid and ObjectId.is_valid(str(tid)):
                    target_task = await db.tasks.find_one({
                        "_id": ObjectId(str(tid)),
                        "completed": {"$ne": True},
                    })
                break

    # 4. Fallback Selection: If no block task is active, select by cognitive energy match
    if not target_task and candidate_tasks:
        clarity = user_state.cognitive_clarity
        energy_preference = "low" if clarity <= 5 else ("high" if clarity >= 8 else "medium")

        # Attempt to match energy requirement
        for t in candidate_tasks:
            if t.get("energy_required") == energy_preference:
                target_task = t
                break

        # Fallback to earliest deadline if no exact energy match
        if not target_task:
            target_task = candidate_tasks[0]

    # 5. Formulate Primary Recommendation
    if target_task:
        task_id_str = str(target_task.get("_id", ""))
        title = target_task.get("title", "Focus Task")
        est_min = target_task.get("estimated_minutes", 25)

        # Apply tactical chunking if cognitive clarity is depleted
        is_chunked = False
        if user_state.cognitive_clarity <= 5 and est_min > 20:
            is_chunked = True
            tactical_action = f"Focus on Part 1 (first 15 min): outline and draft core deliverables for '{title}'."
            why_now = (
                f"Cognitive clarity is {user_state.cognitive_clarity}/10 ({user_state.operating_mode}). "
                f"Task chunked from {est_min}m down to 15m to overcome startup inertia."
            )
        else:
            tactical_action = f"Execute '{title}' during this window."
            why_now = (
                f"Matches current {user_state.operating_mode} capacity ({user_state.cognitive_clarity}/10 clarity). "
                f"Aligned with scheduled block: '{active_block_title or 'On-demand execution'}'."
            )

        primary_rec = TaskRecommendation(
            task_id=task_id_str,
            title=title,
            tactical_action=tactical_action,
            why_now=why_now,
            is_chunked=is_chunked,
        )
    else:
        # Graceful Recharge State when zero tasks remain pending
        primary_rec = TaskRecommendation(
            task_id="recharge_buffer",
            title="Cognitive Recharge & Recovery",
            tactical_action="All scheduled commitments are complete. Step away from screens and rest working memory.",
            why_now="Zero pending tasks in queue. Protecting focus stamina for upcoming blocks.",
            is_chunked=False,
        )

    # 6. Formulate Alternative Recommendations from remaining candidate tasks
    alternatives: List[TaskRecommendation] = []
    if candidate_tasks:
        for alt in candidate_tasks:
            alt_id = str(alt.get("_id", ""))
            if target_task and alt_id == str(target_task.get("_id", "")):
                continue
            alternatives.append(
                TaskRecommendation(
                    task_id=alt_id,
                    title=alt.get("title", "Alternative Task"),
                    tactical_action=f"Work on '{alt.get('title')}' if blocked on primary deliverable.",
                    why_now="Secondary pending priority in queue.",
                    is_chunked=False,
                )
            )
            if len(alternatives) >= 2:
                break

    # 7. Return complete AIRecommendationDecision
    return AIRecommendationDecision(
        user_state_snapshot=user_state,
        primary_recommendation=primary_rec,
        alternative_recommendations=alternatives,
        coaching_note=user_state.coaching_summary or "Baseline focus maintained.",
    )