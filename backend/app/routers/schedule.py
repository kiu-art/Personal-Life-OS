from datetime import datetime, time, timezone
import json
import re
from typing import Any, Dict, List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from app.core.database import get_database
from app.core.user_profile import USER_LIFE_PROFILE
from app.services.state_extractor import state_engine
from app.models.schedule import DynamicDayPlan, ReplanRequest, TimeBlock

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


# --- Time Helpers ---

def time_to_minutes(t_str: Optional[str]) -> int:
    """Converts HH:MM / H:MM strings to minutes since midnight."""
    if not t_str or not isinstance(t_str, str):
        return 0
    match = re.search(r"(\d{1,2}):(\d{2})", t_str)
    if not match:
        return 0
    return int(match.group(1)) * 60 + int(match.group(2))


def minutes_to_time_str(mins: int) -> str:
    """Converts minutes since midnight back into 24-hour HH:MM format."""
    mins = max(0, min(mins, 1439))  # Clamp to 23:59
    h = mins // 60
    m = mins % 60
    return f"{h:02d}:{m:02d}"


def safe_iso_format(dt_val: Any) -> Optional[str]:
    """Safely formats deadlines regardless of input type."""
    if not dt_val:
        return None
    if isinstance(dt_val, str):
        return dt_val
    if hasattr(dt_val, "isoformat"):
        return dt_val.isoformat()
    return str(dt_val)


def create_fallback_block(
    start_time: str,
    end_time: str,
    title: str,
    block_type: str = "deep_work",
    task_id: Optional[str] = None
) -> TimeBlock:
    """Creates a validated TimeBlock instance."""
    fields = getattr(TimeBlock, "model_fields", {})
    kwargs = {
        "start_time": start_time,
        "end_time": end_time,
        "title": title,
    }
    if "block_type" in fields:
        kwargs["block_type"] = block_type
    if "category" in fields:
        kwargs["category"] = "work" if block_type == "deep_work" else "health"
    if "task_id" in fields:
        kwargs["task_id"] = task_id
    if "action_notes" in fields:
        kwargs["action_notes"] = f"Execute {title}."
    if "status_tag" in fields:
        kwargs["status_tag"] = "new"
    if "elasticity" in fields:
        kwargs["elasticity"] = "flexible"
    if "energy_required" in fields:
        kwargs["energy_required"] = "medium"
    if "is_anchor" in fields:
        kwargs["is_anchor"] = False
    return TimeBlock(**kwargs)


def generate_relative_fallback_blocks(current_mins: int, bedtime_mins: int) -> List[TimeBlock]:
    """Generates dynamically spaced blocks starting from current time until bedtime."""
    blocks = []
    cursor = current_mins

    # 1. Focus Sprint (35-45 mins)
    sprint_end = min(cursor + 45, bedtime_mins - 60)
    if sprint_end > cursor:
        blocks.append(create_fallback_block(
            minutes_to_time_str(cursor),
            minutes_to_time_str(sprint_end),
            "Focus Sprint",
            "deep_work"
        ))
        cursor = sprint_end

    # 2. Decompression Buffer (20 mins)
    buffer_end = min(cursor + 20, bedtime_mins - 40)
    if buffer_end > cursor:
        blocks.append(create_fallback_block(
            minutes_to_time_str(cursor),
            minutes_to_time_str(buffer_end),
            "Decompression Break",
            "recharge"
        ))
        cursor = buffer_end

    # 3. Evening Wrap-up / Project Execution
    wrap_end = min(cursor + 60, bedtime_mins - 30)
    if wrap_end > cursor:
        blocks.append(create_fallback_block(
            minutes_to_time_str(cursor),
            minutes_to_time_str(wrap_end),
            "Project Execution",
            "deep_work"
        ))
        cursor = wrap_end

    # 4. Wind Down / Sleep prep (30 mins before bedtime)
    if bedtime_mins > cursor:
        blocks.append(create_fallback_block(
            minutes_to_time_str(cursor),
            minutes_to_time_str(bedtime_mins),
            "Wind Down",
            "buffer"
        ))

    return blocks


# --- Causal Graph Traversal ---

async def get_active_causal_dominoes(db, state_dict: dict, context_note: str) -> List[str]:
    """Traverses db.graph_edges to extract active domino warnings based on current state."""
    active_sources = []
    
    alertness = state_dict.get("physical_alertness", 7)
    clarity = state_dict.get("cognitive_clarity", 7)
    drive = state_dict.get("drive_vs_friction", 7)
    mode = state_dict.get("operating_mode", "steady_neutral")

    if alertness <= 5:
        active_sources.append("low_physical_alertness")
    if clarity <= 5:
        active_sources.append("cognitive_depletion")
    if drive <= 5 or mode == "friction_locked":
        active_sources.append("high_friction")

    note_lower = context_note.lower()
    if "headache" in note_lower:
        active_sources.append("morning_headache")
    if "sleep" in note_lower or "6h" in note_lower or "tired" in note_lower:
        active_sources.append("sleep_deprivation")
    if "traffic" in note_lower or "delay" in note_lower or "late" in note_lower:
        active_sources.append("schedule_slip")

    if not active_sources:
        return []

    cursor = db.graph_edges.find({
        "source": {"$in": active_sources},
        "weight": {"$gte": 0.55}
    })
    edges = await cursor.to_list(length=10)

    warnings = []
    for e in edges:
        source_name = e.get("source", "").replace("_", " ")
        target_name = e.get("target", "").replace("_", " ")
        weight_pct = int(e.get("weight", 0.7) * 100)
        rule = e.get("intervention_rule", "Limit sprint duration and enforce buffer intervals.")
        warnings.append(
            f"Domino Risk: {source_name} historically triggers {target_name} ({weight_pct}% likelihood). "
            f"Intervention Required: {rule}"
        )

    return warnings


# --- Router Endpoints ---

@router.post("/replan", response_model=DynamicDayPlan)
async def dynamic_replan_day(req: ReplanRequest):
    db = get_database()
    now = datetime.now()
    
    # 1. Cognitive State Vector
    try:
        user_state = await state_engine.get_latest_state()
    except Exception as e:
        print(f"[REPLAN STATE RETRIEVAL ERROR] {e}")
        user_state = None

    state_dict = {
        "operating_mode": getattr(user_state, "operating_mode", "steady_neutral") or "steady_neutral",
        "cognitive_clarity": getattr(user_state, "cognitive_clarity", 7) or 7,
        "physical_alertness": getattr(user_state, "physical_alertness", 7) or 7,
        "drive_vs_friction": getattr(user_state, "drive_vs_friction", 7) or 7,
    }
    coaching_summary = getattr(user_state, "coaching_summary", "Baseline focus state") or "Baseline focus state"

    # 2. Time Boundaries
    current_time_str = getattr(req, "current_time", None) or now.strftime("%H:%M")
    hard_stop_str = getattr(req, "hard_stop_bedtime", None) or "23:30"
    today_str = getattr(req, "target_date", None) or now.strftime("%Y-%m-%d")
    situation_note = getattr(req, "situation_note", None) or coaching_summary
    
    current_mins = time_to_minutes(current_time_str)
    bedtime_mins = time_to_minutes(hard_stop_str)

    # 3. Causal Graph Traversal
    domino_warnings = await get_active_causal_dominoes(db, state_dict, situation_note)
    warnings_prompt_str = "\n".join([f"- {w}" for w in domino_warnings]) if domino_warnings else "None detected."

    # 4. Preserve Past History Blocks
    existing_day_doc = await db.schedules.find_one({"date": today_str})
    past_blocks = []
    if existing_day_doc:
        raw_blocks = existing_day_doc.get("blocks") or existing_day_doc.get("schedule") or []
        for b in raw_blocks:
            end_str = b.get("end_time")
            if end_str and time_to_minutes(end_str) <= current_mins:
                past_blocks.append(b)

    # 5. Fetch Pending Tasks
    cursor = db.tasks.find({
        "status": {"$in": ["pending", "scheduled", "in_progress", None]},
        "completed": {"$ne": True},
    }).sort("deadline", 1).limit(10)
    tasks_db = await cursor.to_list(length=10)

    fixed_anchors = []
    regular_tasks_formatted = []

    for t in tasks_db:
        t_id = str(t.get("_id", ""))
        title = t.get("title", "Untitled Task")
        est_min = t.get("estimated_minutes", 25)
        energy_req = t.get("energy_required", "medium")
        deadline_str = safe_iso_format(t.get("deadline"))
        elasticity = t.get("elasticity", "flexible")

        metadata = t.get("metadata") or {}
        tags = t.get("tags") or []
        meeting_time_str = metadata.get("scheduled_start_time")

        if meeting_time_str:
            if time_to_minutes(meeting_time_str) < current_mins:
                continue
            fixed_anchors.append({
                "task_id": t_id,
                "title": title,
                "scheduled_start_time": meeting_time_str,
                "estimated_minutes": est_min,
            })
        elif elasticity == "fixed" or "meeting" in tags:
            fixed_anchors.append({
                "task_id": t_id,
                "title": title,
                "estimated_minutes": est_min,
            })
        else:
            regular_tasks_formatted.append(
                f"- [TASK_ID: {t_id}] Title: '{title}' | Est: {est_min}m | Energy: {energy_req} | Deadline: {deadline_str or 'Flexible'}"
            )

    candidate_tasks_str = "\n".join(regular_tasks_formatted) or "No urgent pending tasks."

    # 6. Fetch Dynamic Routine Constraints from Life Memory (db.memory_facts)
    memory_cursor = db.memory_facts.find({
        "category": {"$in": ["routines", "preferences", "health"]}
    }).limit(10)
    memory_docs = await memory_cursor.to_list(length=10)
    
    routine_memory_rules = [
        f"- {m.get('object')} ({m.get('summary', '')})"
        for m in memory_docs if m.get("object")
    ]
    routine_rules_str = "\n".join(routine_memory_rules) if routine_memory_rules else "No custom memory constraints."

    # Baseline Routine items
    baseline_routine = USER_LIFE_PROFILE.get("baseline_routine", [])
    future_baseline = [
        item for item in baseline_routine
        if time_to_minutes(item.get("time", "").split("-")[0].strip()) >= current_mins
    ]

    # 7. LLM Chain with Strict Enum Guidance
    llm = ChatOllama(
        model="qwen2.5:7b",
        base_url="http://127.0.0.1:11434",
        temperature=0.15,
        num_ctx=4096,
        num_predict=2048,
    )
    structured_llm = llm.with_structured_output(DynamicDayPlan, method="json_schema")
    
    FORWARD_CONNECTED_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are {user_name}'s Executive Secretary for Personal Life OS.
CRITICAL PLANNING RULES:
1. FORWARD-ONLY PLANNING: Current time is {current_time}. First block starts at {current_time}, conclude by {target_bedtime}.
2. TASK ID BINDING: For candidate tasks, set `task_id` to the exact ID from [TASK_ID: ...]. For baseline routines (dinner, wind down), keep `task_id` null.
3. ALLOWED BLOCK TYPES: You MUST use ONLY one of these exact values for `block_type`:
   - "deep_work"
   - "quick_task"
   - "recharge"
   - "buffer"
   - "routine"
   - "fixed_anchor"
   Do NOT use any other string!
4. CHRONOLOGICAL INTEGRITY: Every block's `end_time` MUST be strictly later than its `start_time` (e.g., 18:35 to 19:15).
5. CAUSAL CONSTRAINTS: Respect the Domino Warnings below (limit sprints, add buffers). Populated interventions go into `vital_warnings`.
6. Format: 24-hour HH:MM.
7. PERSISTENT ROUTINE MEMORIES: Strictly protect all windows listed under 'Learned Routine & Habit Constraints'. For example, if dinner is set between 19:00 and 20:30, schedule that exact window as block_type "recharge" with title "Dinner" and task_id null. Do NOT overlap work tasks across protected routine hours.""",
    ),
    (
        "human",
        """Context:
- Current Time: {current_time}
- Energy Level: Mode: {mode} (Clarity: {clarity}/10, Alertness: {alertness}/10)
- Situation: {situation}
- Bedtime Cutoff: {target_bedtime}

Learned Routine & Habit Constraints (from Memory):
{routine_constraints}

Active Causal Domino Warnings:
{causal_warnings}

Upcoming Fixed Commitments:
{fixed_anchors}

Upcoming Baseline Routine Blocks:
{future_baseline}

Candidate Action Tasks:
{candidate_tasks}

Recalculate schedule forward from {current_time} to {target_bedtime} respecting protected routines.""",
    ),
])

    chain = FORWARD_CONNECTED_PROMPT | structured_llm

    try:
        # Fetch active routine and preference constraints from Life Memory
        memory_cursor = db.memory_facts.find({
            "category": {"$in": ["routines", "preferences", "health"]}
        }).limit(10)
        memory_docs = await memory_cursor.to_list(length=10)

        routine_constraints_list = [
            f"- {m.get('object')} ({m.get('summary', '')})"
            for m in memory_docs if m.get("object")
        ]
        routine_constraints_str = (
            "\n".join(routine_constraints_list)
            if routine_constraints_list
            else "No custom memory constraints."
        )
        plan: DynamicDayPlan = await chain.ainvoke({
            "user_name": USER_LIFE_PROFILE.get("name", "User"),
            "current_time": current_time_str,
            "mode": state_dict["operating_mode"],
            "clarity": state_dict["cognitive_clarity"],
            "alertness": state_dict["physical_alertness"],
            "situation": situation_note,
            "target_bedtime": hard_stop_str,
            "routine_constraints": routine_constraints_str,
            "causal_warnings": warnings_prompt_str,
            "fixed_anchors": json.dumps(fixed_anchors, indent=2) if fixed_anchors else "None remaining",
            "future_baseline": json.dumps(future_baseline, indent=2),
            "candidate_tasks": candidate_tasks_str,
        })
    except Exception as e:
        print(f"[REPLAN INFERENCE EXCEPTION] {e}")
        # DYNAMIC RELATIVE FALLBACK: Never hardcodes fixed hours like 18:00
        fallback_blocks = generate_relative_fallback_blocks(current_mins, bedtime_mins)
        plan = DynamicDayPlan(
            summary_verdict="Recalculated forward schedule with adaptive focus sprints and buffers.",
            schedule=fallback_blocks,
            deferred_tasks=[],
            vital_warnings=domino_warnings,
        )

    # 8. Strict Chronological Sanity Filter
    raw_plan_blocks = getattr(plan, "schedule", None) or getattr(plan, "blocks", [])
    sanitized_future_blocks = []
    
    for block in raw_plan_blocks:
        b_start = time_to_minutes(block.start_time)
        b_end = time_to_minutes(block.end_time)

        # Discard invalid backwards blocks (e.g. 18:32 -> 18:00)
        if b_end <= b_start:
            continue

        # Clamp start time if it starts in the past
        if b_start < current_mins:
            if b_end > current_mins:
                block.start_time = current_time_str
                sanitized_future_blocks.append(block)
        else:
            sanitized_future_blocks.append(block)

    # Fallback to generated relative blocks if everything was filtered out
    if not sanitized_future_blocks:
        sanitized_future_blocks = generate_relative_fallback_blocks(current_mins, bedtime_mins)

    if hasattr(plan, "schedule"):
        plan.schedule = sanitized_future_blocks
    if hasattr(plan, "blocks"):
        plan.blocks = sanitized_future_blocks

    serialized_future = [b.model_dump() for b in sanitized_future_blocks]

    # 9. Sync scheduled tasks in db.tasks
    scheduled_task_ids = [
        ObjectId(b["task_id"]) for b in serialized_future 
        if b.get("task_id") and ObjectId.is_valid(b["task_id"])
    ]
    if scheduled_task_ids:
        await db.tasks.update_many(
            {"_id": {"$in": scheduled_task_ids}},
            {"$set": {"status": "scheduled", "scheduled_date": today_str}}
        )

    # 10. Persist clean schedule to MongoDB
    summary_text = (
        getattr(plan, "summary_verdict", None)
        or getattr(plan, "summary", None)
        or "Schedule recalculated forward."
    )
    vital_warnings_list = getattr(plan, "vital_warnings", None) or domino_warnings

    await db.schedules.update_one(
        {"date": today_str},
        {
            "$set": {
                "date": today_str,
                "last_replanned_at": datetime.now(timezone.utc),
                "current_time_anchor": current_time_str,
                "blocks": serialized_future,
                "schedule_blocks": serialized_future,
                "schedule": serialized_future,
                "past_history": past_blocks,
                "summary": summary_text,
                "summary_verdict": summary_text,
                "triage_rationale": summary_text,
                "deferred_tasks": getattr(plan, "deferred_tasks", []),
                "vital_warnings": vital_warnings_list,
            }
        },
        upsert=True,
    )

    return plan


class ScheduleShiftRequest(BaseModel):
    delta_minutes: int = Field(default=40, description="Minutes to shift downstream schedule forward or backward")
    reason: Optional[str] = Field(default="Voice command adjustment", description="Reason for shift")


@router.post("/shift")
async def shift_schedule(req: ScheduleShiftRequest):
    db = get_database()
    today_str = datetime.now().strftime("%Y-%m-%d")
    doc = await db.schedules.find_one({"date": today_str})
    if not doc:
        doc = await db.schedules.find_one(sort=[("date", -1)])
    if not doc:
        return {"status": "error", "message": "No schedule found for today"}

    raw_blocks = doc.get("blocks") or doc.get("schedule_blocks") or doc.get("schedule") or []
    updated_blocks = []

    for block in raw_blocks:
        b = dict(block)
        status_tag = b.get("status_tag", "")
        category = b.get("category", "")
        # Shift tasks that are not completed and not in_progress (or shift downstream)
        if status_tag != "completed" and category != "Completed" and not b.get("is_anchor", False):
            start_str = b.get("start_time")
            end_str = b.get("end_time")
            if start_str and ":" in start_str:
                parts = start_str.split(":")
                sm = int(parts[0]) * 60 + int(parts[1]) + req.delta_minutes
                sm = max(0, min(sm, 1439))
                b["start_time"] = f"{sm // 60:02d}:{sm % 60:02d}"
            if end_str and ":" in end_str:
                parts = end_str.split(":")
                em = int(parts[0]) * 60 + int(parts[1]) + req.delta_minutes
                em = max(0, min(em, 1439))
                b["end_time"] = f"{em // 60:02d}:{em % 60:02d}"

            if status_tag != "in_progress" and b.get("block_type") != "deep_work":
                b["category"] = "Rescheduled"
        updated_blocks.append(b)

    summary_text = f"You said \"{req.reason}\". Your day shifted +{req.delta_minutes} min."
    await db.schedules.update_one(
        {"_id": doc["_id"]},
        {
            "$set": {
                "blocks": updated_blocks,
                "schedule": updated_blocks,
                "schedule_blocks": updated_blocks,
                "summary": summary_text,
                "summary_verdict": summary_text,
                "triage_rationale": summary_text,
                "last_replanned_at": datetime.now(timezone.utc),
            }
        }
    )

    return {
        "status": "success",
        "delta_minutes": req.delta_minutes,
        "reason": req.reason,
        "summary": summary_text,
        "blocks": updated_blocks,
        "schedule": updated_blocks,
    }


@router.post("/reset")
async def reset_schedule_today():
    """Resets today's schedule to baseline agenda tasks."""
    db = get_database()
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Fetch tasks
    tasks = await db.tasks.find().sort("_id", 1).limit(5).to_list(5)
    t_ids = [str(t["_id"]) for t in tasks]

    blocks = [
        {
            "task_id": t_ids[0] if len(t_ids) > 0 else "task-1",
            "start_time": "08:55",
            "end_time": "09:10",
            "title": "Pay electricity bill",
            "block_type": "admin",
            "category": "Completed",
            "source": "From Gmail",
            "status_tag": "completed",
        },
        {
            "task_id": t_ids[1] if len(t_ids) > 1 else "task-2",
            "start_time": "09:40",
            "end_time": "10:30",
            "title": "Flutter auth flow",
            "block_type": "deep_work",
            "category": "Deep Focus",
            "source": "From Calendar",
            "status_tag": "in_progress",
            "progress": 0.40,
            "focus_timer": "25:00",
        },
        {
            "task_id": t_ids[2] if len(t_ids) > 2 else "task-3",
            "start_time": "11:30",
            "end_time": "12:00",
            "title": "Dev Team Standup",
            "block_type": "meeting",
            "category": "Rescheduled",
            "source": "From WhatsApp",
            "status_tag": "pending",
        },
        {
            "task_id": t_ids[3] if len(t_ids) > 3 else "task-4",
            "start_time": "13:15",
            "end_time": "13:30",
            "title": "Call Aai about Saturday",
            "block_type": "personal",
            "category": "Personal",
            "source": "Heard at 08:42 AM",
            "status_tag": "pending",
        },
        {
            "task_id": t_ids[4] if len(t_ids) > 4 else "task-5",
            "start_time": "15:00",
            "end_time": "15:30",
            "title": "Project update draft",
            "block_type": "email",
            "category": "Email",
            "source": "From Gmail",
            "status_tag": "pending",
        },
    ]

    summary_text = 'You said "I woke up late" at 8:15. Your day shifted +40 min.'
    await db.schedules.update_one(
        {"date": today_str},
        {
            "$set": {
                "date": today_str,
                "blocks": blocks,
                "schedule": blocks,
                "schedule_blocks": blocks,
                "summary": summary_text,
                "summary_verdict": summary_text,
                "triage_rationale": summary_text,
                "last_replanned_at": datetime.now(timezone.utc),
            }
        },
        upsert=True
    )
    return {"status": "success", "blocks": blocks, "summary": summary_text}


@router.get("/today")
@router.get("/{target_date}")
async def get_schedule_for_date(target_date: Optional[str] = None):
    """Fetches the active schedule blocks for a specific date (YYYY-MM-DD or 'today')."""
    db = get_database()
    today_str = datetime.now().strftime("%Y-%m-%d")

    search_date = today_str if (not target_date or target_date.lower() == "today") else target_date

    doc = await db.schedules.find_one({"date": search_date})
    if not doc:
        doc = await db.schedules.find_one(sort=[("date", -1)])

    if not doc:
        return {
            "date": search_date,
            "blocks": [],
            "schedule": [],
            "schedule_blocks": [],
            "vital_warnings": [],
            "deferred_tasks": [],
            "summary": ""
        }

    blocks = doc.get("blocks") or doc.get("schedule_blocks") or doc.get("schedule") or []
    summary_val = doc.get("summary") or doc.get("summary_verdict") or doc.get("triage_rationale") or ""
    return {
        "date": doc.get("date", search_date),
        "blocks": blocks,
        "schedule": blocks,
        "schedule_blocks": blocks,
        "summary": summary_val,
        "summary_verdict": summary_val,
        "triage_rationale": summary_val,
        "vital_warnings": doc.get("vital_warnings", []),
        "deferred_tasks": doc.get("deferred_tasks", []),
    }