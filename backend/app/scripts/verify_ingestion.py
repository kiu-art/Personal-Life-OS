import asyncio
import json
import logging
from app.core.database import init_indexes
from app.workers.gmail_worker import GmailIngestionWorker, decode_mime_header, extract_text_content

logging.basicConfig(level=logging.INFO)

async def main() -> None:
    await init_indexes()
    worker = GmailIngestionWorker()

    print("Checking Gmail inbox for UNSEEN messages...")
    loop = asyncio.get_running_loop()
    messages = await loop.run_in_executor(None, worker._sync_fetch_unseen)

    if not messages:
        print("No UNSEEN messages found in INBOX. Mark an email as unread to test.")
        return

    imap_uid, msg = messages[0]
    subject = decode_mime_header(msg.get("Subject"))
    sender = decode_mime_header(msg.get("From"))
    body = extract_text_content(msg)

    print(f"\n--- Fetched Email [UID: {imap_uid}] ---")
    print(f"From: {sender}")
    print(f"Subject: {subject}")
    print(f"Body Preview:\n{body[:300]}...\n")

    if worker.is_automated_noise(msg, sender):
        print("Status: Skipped (Caught by deterministic noise pre-filter).")
        return

    print("Running Gemini Extractor...")
    parsed = await worker.extractor.extract(sender, subject, body, msg.get("Date"))

    print("\n--- Structured Extraction Result ---")
    print(json.dumps(parsed.model_dump(), indent=2))

if __name__ == "__main__":
    asyncio.run(main())