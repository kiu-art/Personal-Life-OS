from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Literal, Optional
from dateutil import parser as date_parser
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from app.core.database import get_database
from app.models.memory import MemoryFact
from app.models.observation import RawObservation
from app.models.task import Task
from app.services.state_extractor import state_engine
from app.models.disruption import VoiceDisruptionIntent
from app.routers.schedule import dynamic_replan_day, ReplanRequest, shift_schedule, ScheduleShiftRequest
from app.core.user_profile import USER_LIFE_PROFILE

router = APIRouter(prefix="/api/observations", tags=["observations"])


# --- Schemas ---

class ObservationCreateRequest(BaseModel):
    source: Literal["email", "chat", "audio", "manual"] = "chat"
    channel: str = "WhatsApp"
    sender: str
    raw_text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VoiceCheckInRequest(BaseModel):
    transcript: str
    source_device: str = "mobile_mic"


class StrictCommitmentResult(BaseModel):
    is_actionable_task: bool = Field(
        description="True ONLY if there is an explicit promise by user, an explicit approval ('ok', 'on it', 'in'), or a direct professional @tag."
    )
    is_memory_fact: bool = Field(
        description="True ONLY if the user explicitly stated a persistent personal preference, habit, or important goal."
    )
    task_title: Optional[str] = Field(
        default=None,
        description="Concise, imperative task title (e.g., 'Review PR #12', 'Send MongoDB schema update')."
    )
    commitment_type: Literal["self_promise", "explicit_approval", "direct_mention", "none"] = Field(
        default="none",
        description="Validation basis for the task."
    )
    is_professional: bool = Field(
        default=True,
        description="False for domestic chores or casual banter."
    )
    estimated_minutes: int = Field(
        default=5,
        description="Realistic duration. Quick checks/links = 3-5 min; short replies = 5 min; deep work = 30-90 min. NEVER pad short tasks into 15-30 min."
    )
    due_date_iso: Optional[str] = Field(
        default=None,
        description="ISO datetime or null if no explicit time deadline was stated."
    )
    elasticity: Literal["fixed", "flexible"] = "flexible"
    energy_required: Literal["low", "medium", "high"] = "medium"
    reasoning: str = Field(
        description="Reasoning for accepting or rejecting."
    )


# --- Strict Commitment Prompts ---

STRICT_GATE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are the Strict Executive Gatekeeper for {user_name}'s Personal Life OS.
Your #1 priority: PREVENT SCHEDULE NOISE, ELIMINATE TASK CHURN, AND REJECT UNCONFIRMED CHAT.

The User is: {user_name}

=== WHEN TO CREATE A TASK (is_actionable_task = true) ===
A message MUST satisfy at least ONE of these conditions:
1. 'self_promise': The message was sent by {user_name} ('Self') promising to deliver something ("I will review this by 5pm", "let me push the fix").
2. 'explicit_approval': An incoming request was asked by a contact, AND {user_name} replied approving it ("ok", "on it", "i am in", "sure", "will do").
3. 'direct_mention_assignment': An external message directly tags, names, or addresses {user_name} (e.g. '@{user_name}' or direct command) delegating a concrete professional deliverable (e.g., "@{user_name} please update schema by 6", "@{user_name} review PR #88"). THIS OVERRIDES THE NEED FOR PRIOR CONFIRMATION.

=== WHEN TO REJECT COMPLETELY (is_actionable_task = false) ===
- Casual domestic chatter: "pest control kare?", "dinner me kya banaye?", "did you eat?", "pani bhar lo" -> REJECT.
- Unassigned group chatter: "can someone check this?", "mess menu updated?", "who is free?" -> REJECT.
- Unapproved external requests WITHOUT direct mention: Someone asks general questions in a group where {user_name} is NOT directly tagged and has not said "ok" -> REJECT.
- Casual banter, memes, status updates -> REJECT.

=== MEMORY RULES (is_memory_fact = true) ===
- ONLY valid if sent by {user_name} ('Self'). External contacts can NEVER create memory facts.
- Must be a persistent personal preference or long-term habit.

=== REALISTIC DURATION SIZING ===
- Quick review, link click, commit verify, skimming a 1-page doc: 3 to 5 minutes.
- Quick message/email reply: 5 minutes.
- Deep debugging, refactoring, feature architecture: 30 to 60 minutes.""",
    ),
    (
        "human",
        """User Identity: {user_name}
Sender: {sender_role}
Is From User ({user_name}): {is_from_me}
Is User Directly @Tagged / Addressed: {is_tagged}
Is Group Chat: {is_group}

Recent Preceding Chat Context:
{chat_context}

Latest Message Under Review:
"{raw_text}"

Evaluate and output strict JSON.""",
    ),
])


DISRUPTION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You analyze user voice transcripts for schedule disruptions.
Detect if the user explicitly or implicitly states that they missed an event, are running late, overslept, or got derailed.
Be conservative: general complaints about being tired are NOT schedule disruptions unless they state they missed or delayed planned tasks.""",
    ),
    (
        "human",
        "Voice Transcript: \"{transcript}\"\n\nDid a schedule disruption occur?",
    ),
])


# --- Background Processor ---

async def process_observation_background(obs_id: str, raw_obs: RawObservation):
    db = get_database()
    try:
        is_from_me = (
            raw_obs.metadata.get("from_me") is True
            or raw_obs.metadata.get("is_from_me") is True
            or raw_obs.source == "audio"
        )
        is_group = raw_obs.metadata.get("is_group", False)

        # 1. Detect direct @tags
        mentioned_jids = raw_obs.metadata.get("mentioned_jids") or []
        has_tag = bool(mentioned_jids) or bool(re.search(r"@\w+", raw_obs.raw_text))

        # 2. Fetch the last 3 messages from the same chat in MongoDB for approval context
        chat_id = raw_obs.metadata.get("chat_jid") or raw_obs.metadata.get("remote_jid") or raw_obs.sender
        query_filter: Dict[str, Any] = {"channel": raw_obs.channel, "_id": {"$ne": obs_id}}
        if chat_id:
            query_filter["$or"] = [
                {"metadata.chat_jid": chat_id},
                {"metadata.remote_jid": chat_id},
                {"sender": raw_obs.sender},
            ]

        recent_cursor = db.raw_observations.find(query_filter).sort("timestamp", -1).limit(3)
        recent_docs = await recent_cursor.to_list(length=3)
        recent_docs.reverse()

        chat_context = "\n".join([
            f"{'User (Self)' if (d.get('metadata', {}).get('from_me') or d.get('sender') == 'Self') else d.get('sender', 'Contact')}: {d.get('raw_text', '')}"
            for d in recent_docs
        ]) or "No prior context available."

        # 3. Call Qwen with the Strict Commitment Gatekeeper
        llm = ChatOllama(
            model="qwen2.5:7b",
            base_url="http://127.0.0.1:11434",
            temperature=0.1,  # Low temperature for strict compliance
            num_ctx=3072,
        )
        gatekeeper_chain = STRICT_GATE_PROMPT | llm.with_structured_output(
            StrictCommitmentResult, method="json_schema"
        )

        user_name = USER_LIFE_PROFILE.get("name", "Ayush")

        gatekeeper_chain = STRICT_GATE_PROMPT | llm.with_structured_output(
            StrictCommitmentResult, method="json_schema"
        )

        sender_role = f"User ('Self', {user_name})" if is_from_me else f"Contact ('{raw_obs.sender}')"

        triage: StrictCommitmentResult = await gatekeeper_chain.ainvoke({
            "user_name": user_name,  # Fixes the missing variable error
            "sender_role": sender_role,
            "is_from_me": str(is_from_me),
            "is_tagged": str(has_tag),
            "is_group": str(is_group),
            "chat_context": chat_context,
            "raw_text": raw_obs.raw_text,
        })

        # 4. Handle Task Creation (STRICT)
        if triage.is_actionable_task and triage.task_title and triage.commitment_type != "none":
            deadline_dt = None
            if triage.due_date_iso:
                try:
                    deadline_dt = date_parser.parse(triage.due_date_iso)
                except Exception:
                    deadline_dt = None

            # Enforce realistic duration limits (between 3 and 120 mins)
            realistic_duration = max(3, min(triage.estimated_minutes, 120))

            task = Task(
                title=triage.task_title,
                description=(
                    f"Source: WhatsApp ({raw_obs.sender})\n"
                    f"Commitment Proof: {triage.commitment_type}\n"
                    f"Reasoning: {triage.reasoning}\n"
                    f"Original Text: {raw_obs.raw_text}"
                ),
                entity=raw_obs.sender if not is_from_me else None,
                source_observation_id=obs_id,
                deadline=deadline_dt,
                estimated_minutes=realistic_duration,
                elasticity=triage.elasticity,
                energy_required=triage.energy_required,
                tags=["whatsapp", triage.commitment_type, "action_item"],
            )
            await db.tasks.insert_one(task.model_dump())
            print(f"[STRICT TASK CREATED] '{task.title}' ({task.estimated_minutes}m) | Proof: {triage.commitment_type}")

            await db.raw_observations.update_one(
                {"_id": obs_id},
                {
                    "$set": {
                        "processed": True,
                        "processed_at": datetime.now(timezone.utc),
                        "extracted_type": "task",
                        "triage_reason": triage.reasoning,
                    }
                },
            )
            return

        # 5. Handle Memory Facts (STRICT: Self-Only & Persistent)
        if triage.is_memory_fact and is_from_me and triage.task_title:
            memory = MemoryFact(
                category="preferences",
                subject="User",
                predicate="observed_statement",
                object=triage.task_title,
                summary=triage.reasoning,
                confidence=0.9,
                source_event=f"whatsapp_{obs_id}",
                tags=["whatsapp", "self"],
            )
            await db.memory_facts.insert_one(memory.model_dump())
            print(f"[MEMORY RECORDED] {memory.object}")

            await db.raw_observations.update_one(
                {"_id": obs_id},
                {
                    "$set": {
                        "processed": True,
                        "processed_at": datetime.now(timezone.utc),
                        "extracted_type": "memory_fact",
                    }
                },
            )
            return

        # 6. Reject Noise / Unconfirmed Chit-chat (NO FALLBACK TASK CREATED)
        print(f"[IGNORED NOISE] '{raw_obs.raw_text}' -> Discarded: {triage.reasoning}")
        await db.raw_observations.update_one(
            {"_id": obs_id},
            {
                "$set": {
                    "processed": True,
                    "processed_at": datetime.now(timezone.utc),
                    "extracted_type": "ignored_noise",
                    "triage_reason": triage.reasoning,
                }
            },
        )

    except Exception as e:
        print(f"[OBSERVATION ERROR] Failed processing {obs_id}: {e}")


# --- Endpoints ---

@router.post("/")
@router.post("/raw")
async def ingest_raw_observation(
    payload: ObservationCreateRequest,
    background_tasks: BackgroundTasks,
):
    db = get_database()

    # Deduplicate by message ID if present
    msg_id = payload.metadata.get("message_id")
    if msg_id:
        existing = await db.raw_observations.find_one({"metadata.message_id": msg_id})
        if existing:
            return {"status": "skipped", "reason": "already_ingested"}

    raw_obs = RawObservation(
        source=payload.source,
        channel=payload.channel,
        sender=payload.sender,
        raw_text=payload.raw_text,
        metadata=payload.metadata,
    )

    insert_result = await db.raw_observations.insert_one(raw_obs.model_dump())
    obs_id = str(insert_result.inserted_id)

    background_tasks.add_task(process_observation_background, obs_id, raw_obs)

    return {"status": "queued", "observation_id": obs_id}


@router.post("/voice-state-test")
async def test_voice_inference(payload: dict):
    transcript = payload.get("text", "")
    state = await state_engine.infer_and_store_state(transcript)
    return state


@router.post("/voice-checkin")
async def record_voice_checkin(payload: VoiceCheckInRequest):
    db = get_database()
    now_local = datetime.now()
    current_time_str = now_local.strftime("%H:%M")

    # 1. Update cognitive state vector
    state = await state_engine.infer_and_store_state(payload.transcript)

    # 2. Check for schedule disruptions
    try:
        llm = ChatOllama(
            model="qwen2.5:7b",
            base_url="http://127.0.0.1:11434",
            temperature=0.1,
            num_ctx=2048,
        )
        disruption_chain = DISRUPTION_PROMPT | llm.with_structured_output(VoiceDisruptionIntent, method="json_schema")
        disruption: VoiceDisruptionIntent = await disruption_chain.ainvoke({
            "transcript": payload.transcript
        })
    except Exception:
        # Heuristic disruption recognition for English, Hindi, Marathi, Hinglish
        text_lower = payload.transcript.lower()
        is_disruption = any(w in text_lower for w in [
            "late", "delay", "postpone", "traffic", "shift", "thoda late", "woke up late",
            "der ho gayi", "ushir", "reschedule", "uthne me late", "woke up"
        ])
        disruption = VoiceDisruptionIntent(
            is_schedule_disruption=is_disruption,
            disruption_type="overslept" if ("late" in text_lower or "woke" in text_lower) else "general_pivot",
            missed_event_description=payload.transcript if is_disruption else None,
            severity="moderate",
            suggested_action="Shift downstream schedule forward",
        )

    replan_result = None

    # 3. If disruption confirmed, trigger the Dynamic Replanner
    if disruption.is_schedule_disruption:
        print(f"[DISRUPTION DETECTED] {disruption.disruption_type}: {disruption.missed_event_description}. Auto-replanning...")
        
        # Shift downstream tasks in MongoDB by 40 minutes and update summary
        shift_res = await shift_schedule(ScheduleShiftRequest(
            delta_minutes=40,
            reason=payload.transcript,
        ))

        replan_result = shift_res

    # 4. Save raw observation
    await db.raw_observations.insert_one({
        "source": "audio",
        "channel": "VoiceNote",
        "sender": "Self",
        "raw_text": payload.transcript,
        "metadata": {
            "operating_mode": state.operating_mode,
            "disruption_detected": disruption.is_schedule_disruption,
        },
        "timestamp": datetime.now(timezone.utc),
        "processed": True,
    })

    return {
        "status": "success",
        "operating_mode": state.operating_mode,
        "disruption_detected": disruption.is_schedule_disruption,
        "coaching_summary": state.coaching_summary,
        "schedule_replanned": replan_result is not None,
        "updated_plan": replan_result,
    }