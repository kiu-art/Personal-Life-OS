from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.database import get_database
from app.services.state_extractor import state_engine

router = APIRouter(prefix="/api/life-map", tags=["life-map"])


class LifeMapNode(BaseModel):
    id: str
    label: str
    node_type: str  # "state" | "person" | "preference" | "routine" | "project" | "symptom"
    category: str
    is_active: bool = False
    weight: float = 1.0
    details: Optional[str] = None


class LifeMapEdge(BaseModel):
    source: str
    target: str
    relation: str  # "causal" | "collaborates_with" | "protects" | "depends_on"
    weight: float = 0.5
    confidence: float = 0.8
    intervention_rule: Optional[str] = None


class UnifiedLifeMapResponse(BaseModel):
    nodes: List[LifeMapNode]
    edges: List[LifeMapEdge]
    active_node_count: int
    graph_health_score: float  # Resilience score based on active risks


@router.get("/", response_model=UnifiedLifeMapResponse)
async def get_unified_life_map():
    db = get_database()
    nodes_map: Dict[str, LifeMapNode] = {}
    edges_list: List[LifeMapEdge] = []

    # 1. Fetch Current Cognitive State to mark active nodes
    try:
        user_state = await state_engine.get_latest_state()
    except Exception:
        user_state = None

    current_mode = getattr(user_state, "operating_mode", "steady_neutral")
    alertness = getattr(user_state, "physical_alertness", 7)
    clarity = getattr(user_state, "cognitive_clarity", 7)

    # 2. Ingest Cognitive State Nodes
    state_node_id = f"state_{current_mode}"
    nodes_map[state_node_id] = LifeMapNode(
        id=state_node_id,
        label=current_mode.replace("_", " ").title(),
        node_type="state",
        category="cognitive",
        is_active=True,
        details=f"Alertness: {alertness}/10, Clarity: {clarity}/10",
    )

    if alertness <= 5:
        nodes_map["low_physical_alertness"] = LifeMapNode(
            id="low_physical_alertness",
            label="Low Physical Alertness",
            node_type="symptom",
            category="health",
            is_active=True,
        )

    if clarity <= 5:
        nodes_map["cognitive_depletion"] = LifeMapNode(
            id="cognitive_depletion",
            label="Cognitive Depletion",
            node_type="symptom",
            category="health",
            is_active=True,
        )

    # 3. Merge Memory Facts into Nodes & Relational Edges
    memories = await db.memory_facts.find({}).to_list(length=50)
    for m in memories:
        category = m.get("category", "general")
        obj_text = m.get("object", "")
        node_id = f"mem_{str(m.get('_id'))}"

        # Clean label for the node
        label = obj_text[:35] + "..." if len(obj_text) > 35 else obj_text

        nodes_map[node_id] = LifeMapNode(
            id=node_id,
            label=label,
            node_type=category,
            category=category,
            is_active=False,
            details=m.get("summary"),
        )

        # Connect user state to memory if relevant
        if category in ["preferences", "routines"]:
            edges_list.append(
                LifeMapEdge(
                    source=state_node_id,
                    target=node_id,
                    relation="governs",
                    weight=0.7,
                    confidence=m.get("confidence", 0.9),
                )
            )

    # 4. Merge Causal Graph Edges into the Map
    causal_edges = await db.graph_edges.find({}).to_list(length=50)
    for ce in causal_edges:
        src = ce.get("source")
        tgt = ce.get("target")

        # Ensure source and target exist as nodes
        if src not in nodes_map:
            nodes_map[src] = LifeMapNode(
                id=src,
                label=src.replace("_", " ").title(),
                node_type="symptom" if "headache" in src or "depletion" in src else "state",
                category="causal_node",
                is_active=(src in ["low_physical_alertness", "cognitive_depletion"]),
            )

        if tgt not in nodes_map:
            nodes_map[tgt] = LifeMapNode(
                id=tgt,
                label=tgt.replace("_", " ").title(),
                node_type="state",
                category="causal_node",
                is_active=False,
            )

        edges_list.append(
            LifeMapEdge(
                source=src,
                target=tgt,
                relation="causal",
                weight=ce.get("weight", 0.7),
                confidence=ce.get("weight", 0.7),
                intervention_rule=ce.get("intervention_rule"),
            )
        )

    # 5. Compute System Resilience Score
    active_risks = [n for n in nodes_map.values() if n.is_active and n.node_type == "symptom"]
    health_score = max(0.2, 1.0 - (len(active_risks) * 0.25))

    return UnifiedLifeMapResponse(
        nodes=list(nodes_map.values()),
        edges=edges_list,
        active_node_count=sum(1 for n in nodes_map.values() if n.is_active),
        graph_health_score=round(health_score, 2),
    )