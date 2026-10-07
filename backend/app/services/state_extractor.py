from datetime import datetime, timezone
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from app.models.user_state import UserStateVector
from app.core.database import get_database

STATE_EVALUATION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are the psycho-cognitive state analyzer for a Personal Life OS.
Your job is to read raw transcriptions of the user's voice throughout the day and infer their current cognitive capacity, mental energy, and resistance.

Guidelines for Inference:
1. Physical Alertness (1-10): Look for mentions of sleep, grogginess, yawning/sighs, caffeine, or illness.
2. Cognitive Clarity (1-10): Look at thought coherence. Rambling, sentence fragments, and complaints about confusion indicate low clarity (1-3). Precise, articulate descriptions indicate high clarity (8-10).
3. Drive vs. Friction (1-10): Complaints, dread, hesitation, and procrastination language indicate friction (1-3). Excitement and clear intent indicate high drive (8-10).

Operating Modes:
- 'deep_flow': High clarity (>=7), high drive (>=7).
- 'restless_scattered': Physical alertness high (>=7), but clarity low (<=4).
- 'friction_locked': User wants to do something but expresses dread, anxiety, or resistance.
- 'cognitive_depletion': Clarity is fried (<=3) after long hours of work.
- 'passive_absorption': Moderate alertness, low stress, receptive to input.
- 'steady_neutral': Standard balanced baseline.

Be realistic and unvarnished. Do not flatter the user.""",
    ),
    (
        "human",
        """Current Time: {current_time}
Recent Voice Transcript / Spoken Utterance:
"{transcript}"

Analyze the user's operational state.""",
    ),
])


class StateEngine:
    def __init__(self):
        self.llm = ChatOllama(
            model="qwen2.5:7b",
            base_url="http://127.0.0.1:11434",
            temperature=0.1,
            num_ctx=2048,
        )
        self.extractor = self.llm.with_structured_output(UserStateVector, method="json_schema")
        self.chain = STATE_EVALUATION_PROMPT | self.extractor

    async def infer_and_store_state(self, transcript: str) -> UserStateVector:
        now = datetime.now(timezone.utc)
        result: UserStateVector = await self.chain.ainvoke({
            "current_time": now.strftime("%Y-%m-%d %H:%M UTC"),
            "transcript": transcript,
        })

        # Save state snapshot in MongoDB time-series collection
        db = get_database()
        await db.user_states.insert_one(result.model_dump())
        return result

    async def get_latest_state(self) -> Optional[UserStateVector]:
        db = get_database()
        doc = await db.user_states.find_one(sort=[("timestamp", -1)])
        if doc:
            return UserStateVector(**doc)
        # Default fallback baseline if no voice notes have been recorded
        return UserStateVector(
            physical_alertness=6,
            cognitive_clarity=6,
            drive_vs_friction=6,
            operating_mode="steady_neutral",
            trigger_evidence=["System default baseline"],
            coaching_summary="Operating at standard baseline capacity.",
        )

state_engine = StateEngine()