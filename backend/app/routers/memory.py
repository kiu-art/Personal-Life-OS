from datetime import datetime, timezone
import re
from typing import List, Optional
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query, status

from app.core.database import get_database
from app.models.memory import (
    CategorizedMemoryResponse,
    MemoryFactResponse,
)

router = APIRouter(prefix="/api/memory", tags=["memory"])


def serialize_memory(doc: dict) -> MemoryFactResponse:
    """Helper to transform Mongo document ObjectId to string id."""
    return MemoryFactResponse(
        id=str(doc["_id"]),
        category=doc.get("category", "general"),
        subject=doc.get("subject", "Unknown"),
        predicate=doc.get("predicate", ""),
        object=doc.get("object", ""),
        summary=doc.get("summary", ""),
        confidence=doc.get("confidence", 1.0),
        source_event=doc.get("source_event"),
        tags=doc.get("tags", []),
        created_at=doc.get("created_at", datetime.now(timezone.utc)),
    )


# 1. Inspect Stored Facts (Filtered List or Search)
@router.get("", response_model=List[MemoryFactResponse])
async def list_memories(
    category: Optional[str] = Query(
        default=None,
        description="Filter by category (e.g. 'preferences', 'people', 'goals', 'health')",
    ),
    subject: Optional[str] = Query(
        default=None,
        description="Filter by subject entity (e.g. 'Rahul', 'Ayush')",
    ),
    q: Optional[str] = Query(
        default=None,
        description="Keyword search across memory summaries and objects",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
):
    """Returns stored facts with optional filtering and pagination."""
    db = get_database()
    query_filter = {}

    if category:
        query_filter["category"] = category.strip().lower()

    if subject:
        query_filter["subject"] = {"$regex": f"^{re.escape(subject.strip())}$", "$options": "i"}

    if q:
        # Case-insensitive regex across summary and object text
        escaped_q = re.escape(q.strip())
        query_filter["$or"] = [
            {"summary": {"$regex": escaped_q, "$options": "i"}},
            {"object": {"$regex": escaped_q, "$options": "i"}},
            {"tags": {"$in": [q.strip().lower()]}},
        ]

    cursor = (
        db.memory_facts.find(query_filter)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)

    return [serialize_memory(doc) for doc in docs]


# 2. "About You" Structured Overview
@router.get("/about-me", response_model=CategorizedMemoryResponse)
async def get_about_me_summary():
    """Groups all stored memories into structured life domains."""
    db = get_database()
    cursor = db.memory_facts.find().sort("created_at", -1)
    docs = await cursor.to_list(length=500)

    categorized: dict[str, List[MemoryFactResponse]] = {}
    for doc in docs:
        item = serialize_memory(doc)
        cat = item.category.lower()
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(item)

    return CategorizedMemoryResponse(
        total_facts=len(docs),
        categories=categorized,
    )


# 3. Permanently Forget a Memory
@router.delete("/{memory_id}", status_code=status.HTTP_200_OK)
async def forget_memory(memory_id: str):
    """Permanently deletes a specific memory fact from the Life OS database."""
    # Validate ObjectId format
    if not ObjectId.is_valid(memory_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid memory ID format: '{memory_id}'",
        )

    db = get_database()
    result = await db.memory_facts.delete_one({"_id": ObjectId(memory_id)})

    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory with ID '{memory_id}' not found",
        )

    return {
        "status": "deleted",
        "deleted_id": memory_id,
        "message": "Memory permanently removed from Life OS.",
    }