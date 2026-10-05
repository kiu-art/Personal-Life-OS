import json
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from app.models.extraction import ObservationTriageResult, ExtractedTask

STRICT_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are the Strict Executive Gatekeeper for a Personal Life OS.
Your primary directive is to ELIMINATE TASK CHURN and PREVENT SCHEDULE NOISE.

=== THE COMMITMENT RULE (ABSOLUTE) ===
A message or conversation snippet CANNOT become a task unless ONE of these 3 conditions is met:
1. 'self_promise': The user explicitly said they will do something (e.g., 'I will send the doc by 5', 'let me fix this').
2. 'explicit_approval': Someone requested something from the user AND the user confirmed with ('ok', 'on it', 'I am in', 'sure', 'will do', 'done').
3. 'direct_mention_urgent': The message contains a direct tag (@user, @Ayush) demanding a concrete professional deliverable or immediate review.

=== STRICT NEGATIVE EXAMPLES (MUST REJECT -> actionable: false) ===
- Casual domestic questions: "pest control kare?", "dinner me kya banaye?", "did you eat?" -> REJECT (rejection_reason: "unconfirmed domestic question").
- Unconfirmed group questions: "mess menu updated?", "who is coming to gym?" -> REJECT (rejection_reason: "general chatter").
- Casual links/memes without an explicit request to analyze -> REJECT.
- Passive observations: "it is raining outside", "class got canceled" -> REJECT.
- Unapproved requests: Someone says "can you do this?" but user has NOT replied or confirmed -> REJECT (rejection_reason: "awaiting user confirmation").

=== REALISTIC DURATION SIZING (NO UNREALISTIC PADDING) ===
- Reading a 1-page doc or checking a PR link: 3 to 5 minutes (NEVER 15-30 minutes).
- Replying to an email or Slack ping: 3 to 7 minutes.
- Quick verification / status update: 2 to 5 minutes.
- Deep architectural work, coding, writing: 30 to 90 minutes.

Only generate a task if it is a REAL, DEFINED commitment that warrants changing the user's daily calendar.""",
    ),
    (
        "human",
        """Sender: {sender}
Context/Chat History:
{chat_context}

Latest Message: "{raw_text}"
Is User Tagged (@): {is_tagged}

Evaluate with zero tolerance for noise.""",
    ),
])


class StrictExtractionEngine:
    def __init__(self):
        self.llm = ChatOllama(
            model="qwen2.5:7b",
            base_url="http://127.0.0.1:11434",
            temperature=0.1,  # Low temperature for strict determinism
            num_ctx=3072,
        )
        self.chain = STRICT_EXTRACTION_PROMPT | self.llm.with_structured_output(
            ObservationTriageResult, method="json_schema"
        )

    async def triage_message(
        self,
        raw_text: str,
        sender: str,
        chat_context: str = "",
        user_handle: str = "Ayush"
    ) -> ObservationTriageResult:
        # Detect if user was explicitly @tagged
        is_tagged = f"@{user_handle.lower()}" in raw_text.lower() or "@you" in raw_text.lower()

        try:
            result: ObservationTriageResult = await self.chain.ainvoke({
                "sender": sender,
                "chat_context": chat_context or "No preceding context provided.",
                "raw_text": raw_text,
                "is_tagged": str(is_tagged),
            })
            return result
        except Exception as e:
            print(f"[EXTRACTION ERROR] {e}")
            return ObservationTriageResult(
                actionable=False,
                rejection_reason=f"Extraction failed: {str(e)}"
            )


strict_extractor = StrictExtractionEngine()