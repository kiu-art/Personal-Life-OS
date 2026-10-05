from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.core.database import get_database
from app.models.review import WeeklyReview
from app.services.review_engine import weekly_review_engine

router = APIRouter(prefix="/api/review/weekly", tags=["weekly_review"])


def sanitize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Safely handles MongoDB ObjectId and converts to Pydantic-compatible dict."""
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


@router.post("/generate", response_model=WeeklyReview)
async def generate_weekly_review(
    end_date: Optional[str] = Query(
        default=None,
        description="End date of the 7-day window in YYYY-MM-DD format (defaults to today/Sunday)",
    )
):
    """
    Triggers 7-day pattern mining, saves the retrospective to MongoDB,
    and automatically feeds discovered behavioral patterns into the Causal Graph.
    """
    db = get_database()
    review = await weekly_review_engine.generate_weekly_review(end_date)

    # --- CLOSED-LOOP: Feed Behavioral Patterns into Causal Graph (db.graph_edges) ---
    patterns = getattr(review, "behavioral_patterns", []) or []
    edges_updated = 0

    for p in patterns:
        trigger = getattr(p, "trigger", None)
        outcome = getattr(p, "observed_outcome", None)
        frequency = getattr(p, "frequency_days", 1)

        if trigger and outcome:
            # Normalize strings to graph node slugs
            source_node = trigger.strip().lower().replace(" ", "_")[:40]
            target_node = outcome.strip().lower().replace(" ", "_")[:40]

            # Calculate confidence weight based on occurrence frequency across the 7 days
            weight = min(0.95, 0.45 + (frequency * 0.10))

            await db.graph_edges.update_one(
                {"source": source_node, "target": target_node},
                {
                    "$set": {
                        "source": source_node,
                        "target": target_node,
                        "source_label": trigger,
                        "target_label": outcome,
                        "relation": "causal",
                        "weight": round(weight, 2),
                        "confidence": 0.85,
                        "occurrences": frequency,
                        "intervention_rule": (
                            f"Weekly pattern observed ({frequency}/7 days): '{trigger}' triggers '{outcome}'. "
                            f"Enforce mitigation: shorten work sprints and protect decompression buffer."
                        ),
                        "origin": "weekly_review",
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
                upsert=True,
            )
            edges_updated += 1

    if edges_updated > 0:
        print(f"[CAUSAL GRAPH UPDATED] Synced {edges_updated} weekly behavioral patterns into db.graph_edges.")

    return review


@router.get("/latest", response_model=WeeklyReview)
async def get_latest_weekly_review():
    """Fetches the most recent weekly review."""
    db = get_database()
    doc = await db.weekly_reviews.find_one(sort=[("week_end_date", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="No weekly reviews generated yet.")
    return WeeklyReview(**sanitize_doc(doc))


@router.get("/history", response_model=List[WeeklyReview])
async def list_weekly_reviews(limit: int = Query(default=10, ge=1, le=52)):
    """Lists past weekly reviews for long-term retrospective tracking."""
    db = get_database()
    cursor = db.weekly_reviews.find().sort("week_end_date", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [WeeklyReview(**sanitize_doc(d)) for d in docs]