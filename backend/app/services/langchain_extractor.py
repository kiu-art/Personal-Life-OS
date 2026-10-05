from typing import Literal, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings
from langchain_ollama import ChatOllama
import datetime

class ParsedLifeItem(BaseModel):
    """Structured extraction output from communication streams."""
    item_type: Literal["task", "memory_fact", "calendar_event", "noise"] = Field(
        description="Categorize into actionable task, long-term personal memory fact, calendar appointment, or noise/spam."
    )
    title: str = Field(
        description="Clear, concise, action-oriented title or fact summary."
    )
    entity: Optional[str] = Field(
        default=None,
        description="Person, project, or organization involved (e.g., 'Rahul', 'DTR Project')."
    )
    due_date_iso: Optional[str] = Field(
        default=None,
        description="Extracted deadline or event timestamp in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS) if explicitly or implicitly mentioned."
    )
    estimated_minutes: Optional[int] = Field(
        default=30,
        description="Estimated duration in minutes required to complete the task."
    )
    elasticity: Literal["fixed", "flexible", "liquid"] = Field(
        default="flexible",
        description="'fixed' for hard appointments/meetings; 'flexible' for focus tasks; 'liquid' for minor chores."
    )
    energy_required: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="'high' for creative/deep focus, 'medium' for standard execution, 'low' for admin/quick replies."
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0."
    )
    reasoning: str = Field(
        description="Brief 1-sentence rationale for the classification."
    )


# System prompt template
EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are the intelligence engine of a Personal Life OS.
Your role is to analyze incoming raw text (emails, messages, transcripts) and extract actionable tasks or long-term personal facts.

Date Resolution Rules:
- The current reference timestamp is: {current_time}.
- If the text mentions 'tomorrow', calculate the exact date for tomorrow and return it as an ISO 8601 string (e.g., '2026-10-06T18:00:00Z').
- If a time is not specified for a deadline (e.g. 'by tomorrow'), default to end of day (18:00 or 23:59).
- Always return 'due_date_iso' in valid ISO format whenever a relative or absolute date is mentioned.

Rules:
1. 'task': Actionable commitments, deadlines, submissions, requests, or reviews required from the user.
2. 'memory_fact': Personal preferences, habits, relationship facts, or goals stated in the communication.
3. 'calendar_event': Fixed scheduled meetings, appointments, or webinars.
4. 'noise': Marketing, promotional content, automated receipts, newsletters, OTPs, or passive chatter with zero action items.
5. If the item is 'noise', keep title short and set confidence high.
6. Estimate realistic duration in minutes if it's a task.
"""
    ),
    (
        "human",
        """Source: {source} ({channel})
Sender: {sender}
Subject/Context: {context}

Raw Content:
{raw_text}
"""
    )
])


class LangChainExtractor:
    def __init__(self):
        self.llm = ChatOllama(
            model="qwen2.5:7b",
            temperature=0.1,
            format="json",  # Forces strict JSON generation
        )
        self.structured_llm = self.llm.with_structured_output(ParsedLifeItem)
        self.chain = EXTRACTION_PROMPT | self.structured_llm

    async def parse_text(
        self,
        raw_text: str,
        sender: str,
        context: str = "",
        source: str = "email",
        channel: str = "Gmail"
    ) -> ParsedLifeItem:
        now = datetime.datetime.now()
        current_time_str = now.strftime("%A, %Y-%m-%d %H:%M:%S")
        """Invokes the LangChain extraction chain asynchronously."""
        return await self.chain.ainvoke({
            "source": source,
            "channel": channel,
            "sender": sender,
            "context": context,
            "current_time":current_time_str,
            "raw_text": raw_text[:3000]  # Cap input length to prevent token bloat
        })


extractor_service = LangChainExtractor()