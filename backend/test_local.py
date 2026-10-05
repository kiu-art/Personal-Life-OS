import asyncio
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama


# 1. Pydantic schema
class ParsedLifeItem(BaseModel):
    item_type: Literal["task", "memory_fact", "calendar_event", "noise"] = Field(
        description="Categorize into task, memory_fact, calendar_event, or noise."
    )
    title: str = Field(description="Concise, action-oriented title or fact summary.")
    entity: Optional[str] = Field(
        default=None,
        description="Person, project, or organization involved (e.g. 'Rahul').",
    )
    due_date_iso: Optional[str] = Field(
        default=None,
        description="Extracted deadline or event timestamp in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).",
    )
    estimated_minutes: Optional[int] = Field(
        default=30,
        description="Estimated duration in minutes required to complete the task.",
    )
    elasticity: Literal["fixed", "flexible", "liquid"] = Field(
        default="flexible",
        description="'fixed' for hard appointments; 'flexible' for focus tasks; 'liquid' for low-priority chores.",
    )
    energy_required: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="'high' for deep focus/coding, 'medium' for standard execution, 'low' for admin tasks.",
    )
    confidence: float = Field(description="Confidence score between 0.0 and 1.0.")
    reasoning: str = Field(description="1-sentence rationale for the classification.")


# 2. Extraction Prompt with dynamic time anchor
PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are the intelligence engine of a Personal Life OS.
Analyze incoming raw text and extract actionable commitments or facts into structured data.

Rules:
1. 'task': Actionable commitments, assignments, deadlines, reviews required from the user.
2. 'memory_fact': Personal preferences, habits, relationship facts, or goals.
3. 'calendar_event': Fixed scheduled meetings, appointments, or syncs.
4. 'noise': Automated receipts, marketing, spam, newsletters, or passive chatter with zero action items.
5. If relative dates like 'tomorrow' or 'Friday 5 PM' appear, calculate the exact ISO date using the Current Reference Time.
6. Extract named individuals or projects into 'entity'.""",
    ),
    (
        "human",
        """Source: {source} ({channel})
Sender: {sender}
Current Reference Time: {current_time}
Subject/Context: {context}

Raw Content:
{raw_text}""",
    ),
])


async def run_local_test():
    print("=" * 60)
    print("Initializing Llama 3.1 (8B) on GPU via Ollama...")
    print("=" * 60)

    # 3. DO NOT include format="json" here when using with_structured_output!
    llm = ChatOllama(
        model="qwen2.5:7b",
        temperature=0.1,
        num_ctx=2048,  # Keeps KV cache lightweight for GPU fit
    )

    # 4. Use json_schema method for strict Ollama structured output
    structured_llm = llm.with_structured_output(ParsedLifeItem, method="json_schema")
    chain = PROMPT_TEMPLATE | structured_llm

    # 5. Test email with current timestamp
    now_str = datetime.now().strftime("%Y-%m-%d %A %H:%M")
    test_sender = "rahul@collegelab.org"
    test_subject = "Urgent: Project Proposal Submission"
    test_body = (
        "Hey Ayush,\n\n"
        "Can you please finalize the architecture diagram and submit the project proposal "
        "draft before Friday 5:00 PM? We need to review it before next week's presentation. "
        "It will probably take about an hour to wrap up.\n\n"
        "Thanks!"
    )

    print(f"Current Reference Time: {now_str}")
    print("Running inference on local GPU (no internet or API quota used)...")

    import time
    start_time = time.perf_counter()

    result: ParsedLifeItem = await chain.ainvoke({
        "source": "email",
        "channel": "Gmail",
        "sender": test_sender,
        "current_time": now_str,
        "context": f"Subject: {test_subject}",
        "raw_text": test_body,
    })

    elapsed = time.perf_counter() - start_time

    # 6. Output validation
    print(f"Inference completed in: {elapsed:.2f} seconds\n")
    print("[EXTRACTED STRUCTURED DATA]")
    print(f"Item Type:         {result.item_type}")
    print(f"Title:             {result.title}")
    print(f"Entity:            {result.entity}")
    print(f"Due Date (ISO):    {result.due_date_iso}")
    print(f"Estimated Minutes: {result.estimated_minutes}")
    print(f"Elasticity:        {result.elasticity}")
    print(f"Energy Required:   {result.energy_required}")
    print(f"Confidence:        {result.confidence}")
    print(f"Reasoning:         {result.reasoning}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_local_test())