from datetime import datetime, timezone
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator


class CausalEdgeExtraction(BaseModel):
    source_node: str = Field(
        description="Triggering cause in lowercase snake_case (e.g., 'morning_headache', 'poor_sleep', 'heavy_meeting_morning')"
    )
    source_category: Literal["health", "work", "routine", "mindset", "social"] = Field(
        description="Category of the cause"
    )
    target_node: str = Field(
        description="Resulting effect in lowercase snake_case (e.g., 'cognitive_depletion', 'postponed_coding', 'gym_skipped')"
    )
    target_category: Literal["health", "work", "routine", "mindset", "social"] = Field(
        description="Category of the effect"
    )
    relation: Literal["causes", "worsens", "mitigates", "triggers"] = Field(
        description="Nature of the causal relationship"
    )
    strength: float = Field(
        default=0.7,
        ge=0.1,
        le=1.0,
        description="Confidence/strength of the link (0.1 to 1.0)",
    )
    explanation: str = Field(
        description="Concise description of the link observed today"
    )

    # AUTO-NORMALIZATION: Handles local LLM outputs (e.g., 8 -> 0.8, 70 -> 0.7) before Pydantic checks bounds
    @field_validator("strength", mode="before")
    @classmethod
    def normalize_strength(cls, v: Union[int, float, str]) -> float:
        try:
            val = float(v)
            if 1.0 < val <= 10.0:
                val = val / 10.0
            elif 10.0 < val <= 100.0:
                val = val / 100.0
            return round(min(max(val, 0.1), 1.0), 2)
        except (ValueError, TypeError):
            return 0.7


class DailyCausalExtractionResult(BaseModel):
    core_chain_summary: str = Field(
        description="1-2 sentences summarizing the primary domino effect of the day"
    )
    identified_edges: List[CausalEdgeExtraction] = Field(
        default_factory=list,
        description="List of cause-and-effect pairs identified from today's events",
    )


# Alias so both class names work seamlessly across engine scripts
EnforcedCausalResult = DailyCausalExtractionResult


# --- Graph DTOs for UI Rendering (React Flow / Cytoscape / D3) ---

class GraphNode(BaseModel):
    id: str
    label: str
    category: str
    frequency: int = 1


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relation: str
    weight: float
    evidence_count: int
    latest_explanation: str
    last_observed: datetime


class LifeMapGraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    total_chains_tracked: int