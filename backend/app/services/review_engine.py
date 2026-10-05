from datetime import datetime, time, timedelta, timezone
from collections import Counter
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from app.core.database import get_database
from app.models.review import WeeklyReview

WEEKLY_REVIEW_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are the Executive Life Strategist of a Personal Life OS.
Your mission is to perform a high-level retrospective over the past 7 days to uncover systemic behavioral tendencies.

Guidelines:
1. Focus on Cross-Day Patterns: Do not merely summarize day by day. Find recurrent cause-and-effect loops (e.g., late nights leading to morning task avoidance; high-friction starts resolving after micro-chunking).
2. Honest, Unflinching Tone: Avoid generic productivity platitudes or corporate cheerleading. Speak like a trusted partner who notices reality.
3. Concrete Behavioral Rules: Ground the 'tactical_directive_next_week' in an actual, programmable scheduling action (e.g., time blocks, buffer windows, meeting limits).
4. Extract 1 to 3 distinct 'behavioral_patterns' backed by the weekly evidence.
""",
    ),
    (
        "human",
        """Window: {week_start} to {week_end}

7-Day Digest:
- Daily Stories Summary:
{stories_digest}

- Tasks Completed vs Postponed:
{tasks_digest}

- Cognitive State Distributions:
{cognitive_digest}

- Top Causal Domino Edges from Life Map:
{lifemap_digest}

Synthesize these 7 days into the structured Weekly Review.""",
    ),
])


class WeeklyReviewEngine:
    def __init__(self):
        self.llm = ChatOllama(
            model="qwen2.5:7b",
            base_url="http://127.0.0.1:11434",
            temperature=0.2,
            num_ctx=8192,
            num_predict=3072,
        )
        self.extractor = self.llm.with_structured_output(
            WeeklyReview, method="json_schema"
        )
        self.chain = WEEKLY_REVIEW_PROMPT | self.extractor

    async def generate_weekly_review(self, end_date_str: str = None) -> WeeklyReview:
        db = get_database()

        # 1. Calculate the 7-day UTC boundary
        if end_date_str:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        else:
            end_date = datetime.now(timezone.utc).date()
        
        start_date = end_date - timedelta(days=6)
        
        start_dt = datetime.combine(start_date, time.min).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, time.max).replace(tzinfo=timezone.utc)

        # 2. Fetch past 7 daily stories
        stories_cursor = db.daily_stories.find({
            "date": {"$gte": start_date.strftime("%Y-%m-%d"), "$lte": end_date.strftime("%Y-%m-%d")}
        }).sort("date", 1)
        stories = await stories_cursor.to_list(10)
        
        stories_digest = "\n".join([
            f"- {s.get('date')}: Headline: '{s.get('headline')}'. Wins: {s.get('wins', [])}. Delays: {s.get('friction_and_delays', [])}. Pivot: '{s.get('tomorrow_pivot')}'"
            for s in stories
        ]) or "Daily stories sparse for this period."

        # 3. Fetch Tasks metrics
        completed_tasks_cursor = db.tasks.find({
            "completed": True,
            "updated_at": {"$gte": start_dt, "$lte": end_dt}
        })
        completed_tasks = [t.get("title") for t in await completed_tasks_cursor.to_list(50)]

        pending_tasks_cursor = db.tasks.find({
            "completed": {"$ne": True},
            "status": {"$in": ["pending", "in_progress", None]}
        }).limit(20)
        pending_tasks = [t.get("title") for t in await pending_tasks_cursor.to_list(20)]

        tasks_digest = f"Completed ({len(completed_tasks)}): {completed_tasks[:8]}\nStill Pending/Postponed ({len(pending_tasks)}): {pending_tasks[:8]}"

        # 4. Fetch Cognitive States logged across the week
        states_cursor = db.user_states.find({
            "timestamp": {"$gte": start_dt, "$lte": end_dt}
        })
        states = await states_cursor.to_list(100)
        
        modes = [s.get("operating_mode") for s in states if s.get("operating_mode")]
        mode_counts = Counter(modes)
        dominant_mode = mode_counts.most_common(1)[0][0] if mode_counts else "steady_neutral"
        
        cognitive_digest = f"Total check-ins: {len(states)}. Dominant mode: {dominant_mode}. Mode distribution: {dict(mode_counts)}"

        # 5. Fetch Life Map causal links active this week
        edges_cursor = db.lifemap_edges.find().sort("weight", -1).limit(6)
        edges = await edges_cursor.to_list(6)
        lifemap_digest = "\n".join([
            f"- {e.get('source')} --({e.get('relation')})--> {e.get('target')} (Weight: {e.get('weight')}, Count: {e.get('evidence_count')})"
            for e in edges
        ]) or "No established causal edges."

        # 6. Execute inference
        review: WeeklyReview = await self.chain.ainvoke({
            "week_start": start_date.strftime("%Y-%m-%d"),
            "week_end": end_date.strftime("%Y-%m-%d"),
            "stories_digest": stories_digest,
            "tasks_digest": tasks_digest,
            "cognitive_digest": cognitive_digest,
            "lifemap_digest": lifemap_digest,
        })

        # Set dominant mode dynamically if missing
        if not review.dominant_operating_mode:
            review.dominant_operating_mode = dominant_mode

        # 7. Upsert into MongoDB
        await db.weekly_reviews.update_one(
            {"week_end_date": end_date.strftime("%Y-%m-%d")},
            {"$set": review.model_dump()},
            upsert=True
        )

        return review


weekly_review_engine = WeeklyReviewEngine()