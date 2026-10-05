import logging
from datetime import datetime, timezone
from typing import Literal, Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

class ParsedLifeItem(BaseModel):
    item_type: Literal["task", "memory_fact", "calendar_event", "noise"] = Field(
        description="Classify if this requires action (task), holds reference information (memory_fact), marks a specific date/time (calendar_event), or is non-actionable clutter (noise)."
    )
    title: str = Field(
        description="Concise, concrete imperative summary (e.g., 'Review Q3 contract' or 'Rahul moved to Indiranagar')."
    )
    entity: Optional[str] = Field(
        default=None,
        description="Key person, organization, or project mentioned."
    )
    due_date_iso: Optional[str] = Field(
        default=None,
        description="ISO 8601 formatted date or datetime if an explicit deadline/event date is stated."
    )
    estimated_minutes: Optional[int] = Field(
        default=None,
        description="Rough time estimate in minutes if actionable."
    )
    elasticity: Literal["fixed", "flexible", "liquid"] = Field(
        default="flexible",
        description="'fixed' for hard deadlines, 'flexible' for soft targets, 'liquid' for backlog items."
    )
    energy_required: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="Cognitive load required to complete."
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score between 0.0 and 1.0."
    )
    reasoning: str = Field(
        description="One brief sentence explaining the classification decision."
    )


class GeminiExtractor:
    def __init__(self) -> None:
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL

    async def extract(
        self, sender: str, subject: str, body: str, date_str: Optional[str] = None
    ) -> ParsedLifeItem:
        current_time = datetime.now(timezone.utc).isoformat()
        
        system_instruction = (
            "You are the cognitive extraction engine for a local Personal Life OS. "
            "Analyze incoming emails to extract tasks, memory facts, or calendar events. "
            "Filter promotional messages, automated receipts, system alerts, and generic newsletters as 'noise'. "
            f"The reference current time is {current_time}."
        )

        prompt = f"""
Sender: {sender}
Subject: {subject}
Date: {date_str or 'Unknown'}

Email Body:
{body[:8000]}  # Truncated to avoid context limits on massive threads
"""
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=ParsedLifeItem,
            ),
        )

        if not response.parsed:
            raise ValueError("Gemini failed to return parsed structured output.")
            
        return response.parsed