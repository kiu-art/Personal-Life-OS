from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.database import get_database
from app.services.state_extractor import state_engine
from app.services.causal_engine import causal_engine
from app.routers.schedule import dynamic_replan_day, ReplanRequest

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskStatusUpdate(BaseModel):
    outcome: str = Field(description="'completed' | 'slipped' | 'in_progress'")
    notes: Optional[str] = None


@router.get("/")
async def list_tasks(status: Optional[str] = None):
    db = get_database()
    query = {}
    if status == "pending":
        query = {"completed": {"$ne": True}}
    elif status == "completed":
        query = {"completed": True}

    tasks = await db.tasks.find(query).sort("deadline", 1).limit(20).to_list(20)
    for t in tasks:
        t["id"] = str(t["_id"])
        del t["_id"]
    return {"tasks": tasks}


@router.patch("/{task_id}/complete")
async def complete_task(task_id: str):
    db = get_database()
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=400, detail="Invalid task ID")

    oid = ObjectId(task_id)
    task = await db.tasks.find_one({"_id": oid})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 1. Update task in MongoDB
    await db.tasks.update_one(
        {"_id": oid},
        {"$set": {"completed": True, "status": "completed", "completed_at": datetime.now(timezone.utc)}}
    )

    # 2. Update status in today's active schedule block
    today_str = datetime.now().strftime("%Y-%m-%d")
    await db.schedules.update_one(
        {"date": today_str, "blocks.task_id": task_id},
        {"$set": {"blocks.$.status_tag": "completed"}}
    )

    # 3. Train Causal Graph (Reinforce completion loop)
    state = await state_engine.get_latest_state()
    await causal_engine.record_task_outcome(task_id, "completed", state.operating_mode)

    print(f"[TASK COMPLETED] '{task.get('title')}' - Causal weights reinforced.")
    return {"status": "success", "task_id": task_id, "completed": True}


@router.patch("/{task_id}/slip")
async def slip_task(task_id: str, reason: Optional[str] = "Delayed execution"):
    db = get_database()
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=400, detail="Invalid task ID")

    oid = ObjectId(task_id)
    task = await db.tasks.find_one({"_id": oid})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 1. Train Causal Graph (Reinforce friction/slip domino edge)
    state = await state_engine.get_latest_state()
    await causal_engine.record_task_outcome(task_id, "slipped", state.operating_mode)

    # 2. Trigger automatic dynamic replanning forward
    now_str = datetime.now().strftime("%H:%M")
    replan_req = ReplanRequest(
        current_time=now_str,
        situation_note=f"Task '{task.get('title')}' slipped: {reason}. Recalculate remaining blocks.",
        hard_stop_bedtime="23:30"
    )
    plan = await dynamic_replan_day(replan_req)

    print(f"[TASK SLIP RECORDED] Triggered dynamic replan forward from {now_str}.")
    return {
        "status": "slipped_and_replanned",
        "task_id": task_id,
        "new_schedule_summary": getattr(plan, "summary_verdict", "Replanned forward")
    }