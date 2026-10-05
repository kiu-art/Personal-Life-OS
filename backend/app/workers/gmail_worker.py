import asyncio
import email
from email.header import decode_header
import imaplib
import logging
from typing import Optional, Tuple
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from dateutil import parser as date_parser

from app.core.config import settings
from app.core.database import get_database
from app.models.observation import RawObservation
from app.models.task import Task
from app.models.memory import MemoryFact
from app.services.langchain_extractor import extractor_service

logger = logging.getLogger("uvicorn.error")


def decode_str(header_value: Optional[str]) -> str:
    """Safely decodes RFC 2047 email headers."""
    if not header_value:
        return ""
    decoded_fragments = decode_header(header_value)
    result = []
    for fragment, encoding in decoded_fragments:
        if isinstance(fragment, bytes):
            result.append(fragment.decode(encoding or "utf-8", errors="replace"))
        else:
            result.append(str(fragment))
    return "".join(result)


def extract_body(msg: email.message.Message) -> str:
    """Extracts clean plain text from multipart or HTML email payloads."""
    plain_text = ""
    html_text = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in content_disposition:
                continue

            try:
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                charset = part.get_content_charset() or "utf-8"
                decoded_part = payload.decode(charset, errors="replace")

                if content_type == "text/plain":
                    plain_text += decoded_part + "\n"
                elif content_type == "text/html":
                    html_text += decoded_part + "\n"
            except Exception:
                continue
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="replace")
            if msg.get_content_type() == "text/html":
                html_text = decoded
            else:
                plain_text = decoded

    if plain_text.strip():
        return plain_text.strip()
    
    if html_text.strip():
        soup = BeautifulSoup(html_text, "html.parser")
        for tag in soup(["script", "style", "head", "meta"]):
            tag.decompose()
        return soup.get_text(separator="\n").strip()

    return ""


def is_automated_noise(msg: email.message.Message, sender: str) -> bool:
    """Pre-filters automated messages to avoid unnecessary Gemini API calls."""
    if msg.get("List-Unsubscribe") or msg.get("Auto-Submitted") == "auto-generated":
        return True
    
    precedence = msg.get("Precedence", "").lower()
    if precedence in ["bulk", "list", "junk"]:
        return True

    noise_senders = ["no-reply@", "noreply@", "mailer-daemon@", "notifications@", "donotreply@"]
    sender_lower = sender.lower()
    return any(pattern in sender_lower for pattern in noise_senders)


class GmailWorker:
    def __init__(self):
        self.host = "imap.gmail.com"
        self.port = 993
        self.username = settings.GMAIL_USER
        self.password = settings.GMAIL_APP_PASSWORD

    def _fetch_unseen_emails_sync(self):
        """Blocking IMAP operations executed in a background thread."""
        mail = imaplib.IMAP4_SSL(self.host, self.port)
        mail.login(self.username, self.password)
        mail.select("INBOX")

        status, messages = mail.search(None, "UNSEEN")
        if status != "OK" or not messages[0]:
            mail.close()
            mail.logout()
            return []

        email_ids = messages[0].split()
        fetched_emails = []

        # Process the 10 most recent unread emails per cycle
        for e_id in email_ids[-10:]:
            res, data = mail.fetch(e_id, "(BODY.PEEK[])")
            if res != "OK":
                continue
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            fetched_emails.append(msg)

        mail.close()
        mail.logout()
        return fetched_emails

    async def process_email(self, msg: email.message.Message):
        """Parses, filters, extracts, and stores an individual email message."""
        db = get_database()
        
        msg_id = msg.get("Message-ID", "").strip()
        if not msg_id:
            msg_id = f"fallback_{hash(msg.as_string())}"

        # 1. Deduplication check
        already_processed = await db.processed_emails.find_one({"message_id": msg_id})
        if already_processed:
            return

        sender = decode_str(msg.get("From"))
        subject = decode_str(msg.get("Subject"))
        body = extract_body(msg)

        if not body or len(body.strip()) < 10:
            await db.processed_emails.insert_one({"message_id": msg_id, "status": "empty_body"})
            return

        # 2. Pre-filter marketing/newsletters
        if is_automated_noise(msg, sender):
            await db.processed_emails.insert_one({
                "message_id": msg_id,
                "subject": subject,
                "status": "filtered_noise",
                "processed_at": datetime.now(timezone.utc)
            })
            return

        # 3. Store Initial Raw Observation
        raw_obs = RawObservation(
            source="email",
            channel="Gmail",
            sender=sender,
            raw_text=body,
            metadata={
                "subject": subject,
                "message_id": msg_id
            }
        )
        obs_insert = await db.raw_observations.insert_one(raw_obs.model_dump())
        obs_id = str(obs_insert.inserted_id)

        # 4. Extract structured intent via LangChain + Gemini
        parsed_item = await extractor_service.parse_text(
            raw_text=body,
            sender=sender,
            context=f"Subject: {subject}",
            source="email",
            channel="Gmail"
        )

        # 5. Route structured result to appropriate MongoDB collections
        if parsed_item.item_type in ["task", "calendar_event"]:
            deadline_dt = None
            if parsed_item.due_date_iso:
                try:
                    deadline_dt = date_parser.parse(parsed_item.due_date_iso)
                except Exception:
                    deadline_dt = None

            is_meeting = parsed_item.item_type == "calendar_event"

            new_task = Task(
                title=parsed_item.title,
                description=f"From: {sender}\nSubject: {subject}\nReasoning: {parsed_item.reasoning}",
                entity=parsed_item.entity,
                source_observation_id=obs_id,
                deadline=deadline_dt,
                estimated_minutes=parsed_item.estimated_minutes or (30 if is_meeting else 45),
                elasticity="fixed" if is_meeting else parsed_item.elasticity,
                energy_required=parsed_item.energy_required,
                tags=["email", "gmail", "meeting" if is_meeting else "action_item"]
            )
            await db.tasks.insert_one(new_task.model_dump())
            print(f"[{'EVENT' if is_meeting else 'TASK'} SAVED] {new_task.title} (Time: {new_task.deadline}, Elasticity: {new_task.elasticity})")

        elif parsed_item.item_type == "memory_fact":
            memory = MemoryFact(
                category="work",
                subject=parsed_item.entity or "General",
                predicate="observation",
                object=parsed_item.title,
                summary=parsed_item.reasoning,
                confidence=parsed_item.confidence,
                source_event=f"email_{obs_id}"
            )
            await db.memory_facts.insert_one(memory.model_dump())
            print(f"[MEMORY RECORDED] {memory.summary}")

        # 6. Update the raw observation with completed status
        await db.raw_observations.update_one(
            {"_id": obs_insert.inserted_id},
            {
                "$set": {
                    "processed": True,
                    "processed_at": datetime.now(timezone.utc),
                    "extracted_type": parsed_item.item_type
                }
            }
        )

        # 7. Mark as processed in email deduplication ledger
        await db.processed_emails.insert_one({
            "message_id": msg_id,
            "subject": subject,
            "item_type": parsed_item.item_type,
            "processed_at": datetime.now(timezone.utc)
        })
        """Parses, filters, extracts, and stores an individual email message."""
        db = get_database()
        
        msg_id = msg.get("Message-ID", "").strip()
        if not msg_id:
            msg_id = f"fallback_{hash(msg.as_string())}"

        # Deduplication check
        already_processed = await db.processed_emails.find_one({"message_id": msg_id})
        if already_processed:
            return

        sender = decode_str(msg.get("From"))
        subject = decode_str(msg.get("Subject"))
        body = extract_body(msg)

        if not body or len(body.strip()) < 10:
            await db.processed_emails.insert_one({"message_id": msg_id, "status": "empty_body"})
            return

        # Pre-filter marketing/newsletters
        if is_automated_noise(msg, sender):
            await db.processed_emails.insert_one({
                "message_id": msg_id,
                "subject": subject,
                "status": "filtered_noise",
                "processed_at": datetime.now(timezone.utc)
            })
            return

        # 1. Store Raw Observation
        raw_obs = RawObservation(
            source="email",
            channel="Gmail",
            sender=sender,
            raw_text=body,
            metadata={
                "subject": subject,
                "message_id": msg_id
            }
        )
        obs_insert = await db.raw_observations.insert_one(raw_obs.model_dump())
        obs_id = str(obs_insert.inserted_id)

        # 2. Extract using LangChain + Gemini
        parsed_item = await extractor_service.parse_text(
            raw_text=body,
            sender=sender,
            context=f"Subject: {subject}",
            source="email",
            channel="Gmail"
        )

        # 3. Route to MongoDB collections
        print(parsed_item)
        if parsed_item.item_type == "task":
            deadline_dt = None
            if parsed_item.due_date_iso:
                try:
                    deadline_dt = date_parser.parse(parsed_item.due_date_iso)
                except Exception:
                    deadline_dt = None

            new_task = Task(
                title=parsed_item.title,
                description=f"From: {sender}\nSubject: {subject}\nReasoning: {parsed_item.reasoning}",
                entity=parsed_item.entity,
                source_observation_id=obs_id,
                deadline=deadline_dt,
                estimated_minutes=parsed_item.estimated_minutes or 30,
                elasticity=parsed_item.elasticity,
                energy_required=parsed_item.energy_required,
                tags=["email", "gmail"]
            )
            await db.tasks.insert_one(new_task.model_dump())
            print(f"[TASK CREATED] {new_task.title} (Deadline: {new_task.deadline})")

        elif parsed_item.item_type == "memory_fact":
            memory = MemoryFact(
                category="work",
                subject=parsed_item.entity or "General",
                predicate="observation",
                object=parsed_item.title,
                summary=parsed_item.reasoning,
                confidence=parsed_item.confidence,
                source_event=f"email_{obs_id}"
            )
            await db.memory_facts.insert_one(memory.model_dump())
            print(f"[MEMORY RECORDED] {memory.summary}")

        # Mark as processed
        await db.processed_emails.insert_one({
            "message_id": msg_id,
            "subject": subject,
            "item_type": parsed_item.item_type,
            "processed_at": datetime.now(timezone.utc)
        })

    async def run_once(self):
        """Runs a single polling execution pass."""
        try:
            emails = await asyncio.to_thread(self._fetch_unseen_emails_sync)
            for msg in emails:
                await self.process_email(msg)
        except Exception as e:
            logger.error(f"Error in Gmail worker cycle: {e}")

    async def start_polling(self):
        """Continuous background loop."""
        logger.info(f"Gmail worker started. Polling every {settings.POLL_INTERVAL_SECONDS}s.")
        while True:
            await self.run_once()
            await asyncio.sleep(settings.POLL_INTERVAL_SECONDS)


gmail_worker = GmailWorker()