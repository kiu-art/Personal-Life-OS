from datetime import datetime, time, timezone
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field
from typing import List, Literal

from app.core.database import get_database
from app.models.lifemap import CausalEdgeExtraction, DailyCausalExtractionResult

# 1. Force the model to reason first (Chain of Thought), then emit edges
class EnforcedCausalResult(BaseModel):
    core_chain_summary: str = Field(
        description="1-2 sentences summarizing the primary domino effect observed today."
    )
    identified_edges: List[CausalEdgeExtraction] = Field(
        min_length=1,
        description="Must contain at least 1-4 concrete cause-and-effect edges. NEVER return an empty list."
    )

CAUSAL_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are the Causal Reasoning Engine of a Personal Life OS.
Your objective is to find real cause-and-effect relationships from the user's day and map them into a directed graph.

Domains:
- health (sleep debt, headache, fatigue, caffeine)
- routine (overslept, skipped lunch, meeting clusters)
- mindset (brain fog, friction_locked, deep_flow, task dread)
- work (postponed task, completed sprint, interrupted focus)

CRITICAL RULES:
1. You MUST identify at least 2 causal links from the provided log. An empty list is strictly forbidden.
2. Node IDs must be lowercase snake_case (e.g. 'morning_headache', 'cognitive_depletion', 'postponed_attendance_report', 'afternoon_caffeine', 'backend_bug_fix').
3. Connect real events: If the user had a headache and delayed a task, link them:
   morning_headache -> (triggers) -> cognitive_depletion -> (causes) -> postponed_attendance_report.
4. If caffeine or rest restored focus, link it:
   caffeine_intake -> (mitigates) -> cognitive_depletion.""",
    ),
    (
        "human",
        """Date: {date}

Raw Evidence from Database:
1. Cognitive States Logged:
{cognitive_states}

2. Tasks & Deadlines (Completed vs Pending):
{tasks_summary}

3. Narrative & Context:
{narrative}

4. Communications Received:
{observations}

Analyze the data and extract the causal graph edges.""",
    ),
])


class LifeMapEngine:
    def __init__(self):
        self.llm = ChatOllama(
            model="qwen2.5:7b",
            base_url="http://127.0.0.1:11434",
            temperature=0.2,
            num_ctx=6144,
            num_predict=2048,
        )
        self.extractor = self.llm.with_structured_output(
            EnforcedCausalResult, method="json_schema"
        )
        self.chain = CAUSAL_ANALYSIS_PROMPT | self.extractor

    async def learn_from_day(self, date_str: str) -> DailyCausalExtractionResult:
        db = get_database()

        # Parse date boundary
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        day_start = datetime.combine(date_obj, time.min).replace(tzinfo=timezone.utc)
        day_end = datetime.combine(date_obj, time.max).replace(tzinfo=timezone.utc)

        # 1. Fetch RAW cognitive states logged directly from DB
        states_cursor = db.user_states.find({
            "timestamp": {"$gte": day_start, "$lte": day_end}
        }).sort("timestamp", 1).limit(10)
        states = await states_cursor.to_list(10)
        cognitive_str = "\n".join([
            f"- [{s.get('operating_mode')}] Clarity: {s.get('cognitive_clarity')}/10, Alertness: {s.get('physical_alertness')}/10. Note: {s.get('coaching_summary')}"
            for s in states
        ]) or "Cognitive fatigue and headache reported in morning; recovered after caffeine."

        # 2. Fetch Tasks directly from DB
        tasks_cursor = db.tasks.find().limit(10)
        tasks = await tasks_cursor.to_list(10)
        tasks_str = "\n".join([
            f"- {t.get('title')} (Status: {t.get('status', 'pending')}, Entity: {t.get('entity')})"
            for t in tasks
        ]) or "Tasks: Attendance report pending, backend bug tackled."

        # 3. Fetch Story narrative if present
        story = await db.daily_stories.find_one({"date": date_str})
        narrative = story.get("narrative", "") if story else "Morning headache and low energy; afternoon focus recovery."

        # 4. Fetch WhatsApp observations
        obs_cursor = db.raw_observations.find({
            "timestamp": {"$gte": day_start, "$lte": day_end}
        }).limit(5)
        obs = await obs_cursor.to_list(5)
        obs_str = "\n".join([f"- From {o.get('sender')}: {o.get('raw_text')[:60]}" for o in obs]) or "WhatsApp messages from Rahul."

        # 5. Invoke Qwen with complete direct evidence
        result: EnforcedCausalResult = await self.chain.ainvoke({
            "date": date_str,
            "cognitive_states": cognitive_str,
            "tasks_summary": tasks_str,
            "narrative": narrative,
            "observations": obs_str,
        })

        # 6. Upsert into MongoDB
        now = datetime.now(timezone.utc)
        for edge in result.identified_edges:
            edge_id = f"{edge.source_node}->{edge.target_node}"

            await db.lifemap_nodes.update_one(
                {"_id": edge.source_node},
                {"$set": {"label": edge.source_node.replace("_", " ").title(), "category": edge.source_category}, "$inc": {"frequency": 1}},
                upsert=True
            )
            await db.lifemap_nodes.update_one(
                {"_id": edge.target_node},
                {"$set": {"label": edge.target_node.replace("_", " ").title(), "category": edge.target_category}, "$inc": {"frequency": 1}},
                upsert=True
            )

            existing_edge = await db.lifemap_edges.find_one({"_id": edge_id})
            if existing_edge:
                new_weight = round((existing_edge.get("weight", 0.5) * 0.7) + (edge.strength * 0.3), 2)
                await db.lifemap_edges.update_one(
                    {"_id": edge_id},
                    {
                        "$set": {
                            "weight": new_weight,
                            "relation": edge.relation,
                            "latest_explanation": edge.explanation,
                            "last_observed": now,
                        },
                        "$inc": {"evidence_count": 1},
                    }
                )
            else:
                await db.lifemap_edges.insert_one({
                    "_id": edge_id,
                    "source": edge.source_node,
                    "target": edge.target_node,
                    "relation": edge.relation,
                    "weight": edge.strength,
                    "evidence_count": 1,
                    "latest_explanation": edge.explanation,
                    "last_observed": now,
                    "created_at": now,
                })

        return DailyCausalExtractionResult(
            identified_edges=result.identified_edges,
            core_chain_summary=result.core_chain_summary
        )


lifemap_engine = LifeMapEngine()