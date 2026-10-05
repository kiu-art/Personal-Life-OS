from datetime import datetime, timezone
from typing import List, Optional
from app.core.database import get_database


class CausalGraphEngine:
    async def get_active_domino_risks(self, user_state_dict: dict, context_text: str = "") -> List[str]:
        """
        Traverses db.graph_edges to find active risk dominoes matching current state.
        """
        db = get_database()
        active_conditions = []

        alertness = user_state_dict.get("physical_alertness", 7)
        clarity = user_state_dict.get("cognitive_clarity", 7)
        drive = user_state_dict.get("drive_vs_friction", 7)
        mode = user_state_dict.get("operating_mode", "steady_neutral")

        # Map state vector to graph vertex triggers
        if alertness <= 5:
            active_conditions.append("low_physical_alertness")
        if clarity <= 5:
            active_conditions.append("cognitive_depletion")
        if drive <= 5 or mode == "friction_locked":
            active_conditions.append("high_friction")
        if "headache" in context_text.lower():
            active_conditions.append("morning_headache")
        if "sleep" in context_text.lower() or "6h" in context_text.lower():
            active_conditions.append("sleep_deprivation")

        if not active_conditions:
            return []

        # Traverse edges where source is active and confidence >= 0.6
        cursor = db.graph_edges.find({
            "source": {"$in": active_conditions},
            "weight": {"$gte": 0.55}
        })
        edges = await cursor.to_list(length=10)

        warnings = []
        for e in edges:
            prob = int(e.get("weight", 0.7) * 100)
            src = e.get("source", "").replace("_", " ")
            tgt = e.get("target", "").replace("_", " ")
            rule = e.get("intervention_rule", "Insert mandatory buffer block and cap task at 35 mins.")
            warnings.append(f"Risk Domino: {src} historically triggers {tgt} ({prob}% probability). Intervention: {rule}")

        return warnings

    async def record_task_outcome(self, task_id: str, outcome: str, state_mode: str):
        """
        Closed-loop causal learning: Adjusts edge weights when tasks finish or slip.
        outcome: 'completed' | 'slipped' | 'abandoned'
        """
        db = get_database()
        
        # When a task slips under friction or depletion, reinforce the failure edge
        if outcome in ["slipped", "abandoned"]:
            source_node = "cognitive_depletion" if state_mode == "friction_locked" else "unrealistic_estimation"
            target_node = "schedule_slip"
            
            await db.graph_edges.update_one(
                {"source": source_node, "target": target_node},
                {
                    "$inc": {"occurrences": 1, "weight": 0.05},
                    "$set": {"last_reinforced": datetime.now(timezone.utc)}
                },
                upsert=True
            )
            print(f"[CAUSAL LEARNING] Reinforced edge: {source_node} -> {target_node}")
            
        elif outcome == "completed":
            # Successful execution under pressure weakens the negative edge
            await db.graph_edges.update_one(
                {"source": "short_chunking", "target": "task_completion"},
                {
                    "$inc": {"occurrences": 1, "weight": 0.03},
                    "$set": {"last_reinforced": datetime.now(timezone.utc)}
                },
                upsert=True
            )
            print(f"[CAUSAL LEARNING] Reinforced positive edge: short_chunking -> task_completion")


causal_engine = CausalGraphEngine()