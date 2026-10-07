import logging
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger("uvicorn.error")


class DatabaseManager:
    client = None
    db = None


db_manager = DatabaseManager()


async def _auto_seed_initial_data(db):
    """Seed initial tasks, schedule, and cognitive state if database is empty."""
    tasks_count = await db.tasks.count_documents({})
    if tasks_count == 0:
        logger.info("Initializing database with baseline tasks and today's schedule...")
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        # 1. User state
        await db.user_states.insert_one({
            "operating_mode": "deep_flow",
            "physical_alertness": 8,
            "cognitive_clarity": 9,
            "drive_vs_friction": 8,
            "coaching_summary": "High morning clarity detected. Prime window for architectural design and complex coding.",
            "timestamp": datetime.now(timezone.utc),
            "source": "seed",
        })

        # 2. Baseline Tasks matching Stitch UI
        t1 = {
            "title": "Pay electricity bill",
            "description": "Monthly utility bill payment via net banking",
            "source": "From Gmail",
            "completed": True,
            "status": "completed",
            "deadline": datetime.combine(now.date(), datetime.min.time()) + timedelta(hours=9),
            "estimated_minutes": 10,
            "tags": ["finance", "gmail"],
            "created_at": datetime.now(timezone.utc),
        }
        t2 = {
            "title": "Flutter auth flow",
            "description": "Implement token refresh, middleware guards, and MongoDB schema mappings.",
            "source": "From Calendar",
            "completed": False,
            "status": "in_progress",
            "category": "Deep Focus",
            "deadline": datetime.combine(now.date(), datetime.min.time()) + timedelta(hours=10),
            "estimated_minutes": 45,
            "progress": 0.40,
            "tags": ["coding", "calendar", "deep_focus"],
            "created_at": datetime.now(timezone.utc),
        }
        t3 = {
            "title": "Dev Team Standup",
            "description": "Sprint check-in with frontend and backend developers",
            "source": "From WhatsApp",
            "completed": False,
            "status": "pending",
            "category": "Rescheduled",
            "deadline": datetime.combine(now.date(), datetime.min.time()) + timedelta(hours=11, minutes=30),
            "estimated_minutes": 30,
            "tags": ["whatsapp", "meeting"],
            "created_at": datetime.now(timezone.utc),
        }
        t4 = {
            "title": "Call Aai about Saturday",
            "description": "Confirm weekend family visit timing",
            "source": "Heard at 08:42 AM",
            "completed": False,
            "status": "pending",
            "category": "Personal",
            "deadline": datetime.combine(now.date(), datetime.min.time()) + timedelta(hours=13, minutes=15),
            "estimated_minutes": 15,
            "tags": ["personal", "voice"],
            "created_at": datetime.now(timezone.utc),
        }
        t5 = {
            "title": "Project update draft",
            "description": "Send milestone roadmap to stakeholders",
            "source": "From Gmail",
            "completed": False,
            "status": "pending",
            "category": "Email",
            "deadline": datetime.combine(now.date(), datetime.min.time()) + timedelta(hours=15),
            "estimated_minutes": 25,
            "tags": ["work", "email"],
            "created_at": datetime.now(timezone.utc),
        }

        r1 = await db.tasks.insert_one(t1)
        r2 = await db.tasks.insert_one(t2)
        r3 = await db.tasks.insert_one(t3)
        r4 = await db.tasks.insert_one(t4)
        r5 = await db.tasks.insert_one(t5)

        # 3. Today's initial schedule blocks
        schedule_blocks = [
            {
                "task_id": str(r1.inserted_id),
                "start_time": "08:55",
                "end_time": "09:10",
                "title": "Pay electricity bill",
                "block_type": "admin",
                "category": "Completed",
                "source": "From Gmail",
                "status_tag": "completed",
            },
            {
                "task_id": str(r2.inserted_id),
                "start_time": "09:40",
                "end_time": "10:30",
                "title": "Flutter auth flow",
                "block_type": "deep_work",
                "category": "Deep Focus",
                "source": "From Calendar",
                "status_tag": "in_progress",
                "progress": 0.40,
                "focus_timer": "25:00",
            },
            {
                "task_id": str(r3.inserted_id),
                "start_time": "11:30",
                "end_time": "12:00",
                "title": "Dev Team Standup",
                "block_type": "meeting",
                "category": "Rescheduled",
                "source": "From WhatsApp",
                "status_tag": "pending",
            },
            {
                "task_id": str(r4.inserted_id),
                "start_time": "13:15",
                "end_time": "13:30",
                "title": "Call Aai about Saturday",
                "block_type": "personal",
                "category": "Personal",
                "source": "Heard at 08:42 AM",
                "status_tag": "pending",
            },
            {
                "task_id": str(r5.inserted_id),
                "start_time": "15:00",
                "end_time": "15:30",
                "title": "Project update draft",
                "block_type": "email",
                "category": "Email",
                "source": "From Gmail",
                "status_tag": "pending",
            },
        ]

        await db.schedules.update_one(
            {"date": today_str},
            {
                "$set": {
                    "date": today_str,
                    "blocks": schedule_blocks,
                    "schedule": schedule_blocks,
                    "schedule_blocks": schedule_blocks,
                    "summary": "You said 'I woke up late' at 8:15. Your day shifted +40 min.",
                    "summary_verdict": "You said 'I woke up late' at 8:15. Your day shifted +40 min.",
                    "disruption_notice": 'You said "I woke up late" at 8:15. Your day shifted +40 min.',
                    "day_shift_minutes": 40,
                }
            },
            upsert=True,
        )
        logger.info("Database baseline seeded successfully.")


async def connect_to_mongo() -> None:
    """Initializes the MongoDB connection pool with automatic in-memory fallback."""
    try:
        logger.info("Attempting connection to MongoDB...")
        client = AsyncIOMotorClient(
            settings.MONGO_URI,
            maxPoolSize=10,
            minPoolSize=1,
            serverSelectionTimeoutMS=2000,
        )
        # Verify cluster ping
        await client.admin.command("ping")
        db_manager.client = client
        db_manager.db = client[settings.DB_NAME]
        logger.info(f"Connected to MongoDB database: '{settings.DB_NAME}'")
    except Exception as e:
        logger.warning(f"Could not connect to live MongoDB server ({e}). Falling back to in-memory asynchronous database engine.")
        from mongomock_motor import AsyncMongoMockClient
        db_manager.client = AsyncMongoMockClient()
        db_manager.db = db_manager.client[settings.DB_NAME]
        logger.info(f"Initialized reactive in-memory MongoDB database '{settings.DB_NAME}'.")

    # Ensure baseline data is ready
    await _auto_seed_initial_data(db_manager.db)


async def close_mongo_connection() -> None:
    """Closes all active MongoDB connection pools."""
    if db_manager.client:
        logger.info("Closing MongoDB connection pool...")
        try:
            db_manager.client.close()
        except Exception:
            pass
        logger.info("MongoDB connection closed.")


def get_database():
    """Dependency helper to access the active database instance."""
    if db_manager.db is None:
        raise RuntimeError("Database client is not initialized. Call connect_to_mongo() first.")
    return db_manager.db