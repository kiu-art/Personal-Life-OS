import asyncio
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Load .env first so MONGO_URI and settings match FastAPI exactly
load_dotenv()

from app.core.database import connect_to_mongo, get_database


async def seed_database():
    await connect_to_mongo()
    db = get_database()
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    print(f"Connected to MongoDB via app core -> Database: {db.name}")

    # ==========================================
    # 1. SEED COGNITIVE STATE (Top Status Pill)
    # ==========================================
    print("Seeding Cognitive State...")
    await db.user_states.delete_many({"source": "seed"})
    await db.user_states.insert_one({
        "operating_mode": "deep_flow",
        "physical_alertness": 8,
        "cognitive_clarity": 9,
        "drive_vs_friction": 8,
        "coaching_summary": "High morning clarity detected. Prime window for architectural design and complex coding.",
        "timestamp": datetime.now(timezone.utc),
        "source": "seed",
    })

    # ==========================================
    # 2. SEED TASKS (For "What next?" / WSIDN)
    # ==========================================
    print("Seeding Pending Tasks...")
    await db.tasks.delete_many({"source": "seed"})

    sample_tasks = [
        {
            "title": "Review commit diffs for authentication module",
            "description": "Verify token expiry, middleware guards, and MongoDB schema mappings.",
            "estimated_minutes": 25,
            "energy_required": "high",
            "deadline": datetime.combine(now.date(), datetime.min.time()) + timedelta(hours=18),
            "elasticity": "flexible",
            "completed": False,
            "status": "pending",
            "tags": ["work", "action_item", "code"],
            "source": "seed",
            "created_at": datetime.now(timezone.utc),
        },
        {
            "title": "Send updated API schema notes to Rahul",
            "description": "Outline the new dynamic schedule endpoints and request schemas.",
            "estimated_minutes": 15,
            "energy_required": "medium",
            "deadline": datetime.combine(now.date(), datetime.min.time()) + timedelta(hours=20),
            "elasticity": "flexible",
            "completed": False,
            "status": "pending",
            "tags": ["work", "action_item"],
            "source": "seed",
            "created_at": datetime.now(timezone.utc),
        },
        {
            "title": "Verify Expo app build on physical Android device",
            "description": "Ensure navigation between Companion, Schedule, and Brain tabs is smooth.",
            "estimated_minutes": 10,
            "energy_required": "low",
            "deadline": None,
            "elasticity": "flexible",
            "completed": False,
            "status": "pending",
            "tags": ["mobile", "testing"],
            "source": "seed",
            "created_at": datetime.now(timezone.utc),
        },
        {
            "title": "Evening Architecture Sync",
            "description": "Fixed project discussion on Google Meet.",
            "estimated_minutes": 30,
            "energy_required": "high",
            "deadline": datetime.combine(now.date(), datetime.min.time()) + timedelta(hours=19),
            "elasticity": "fixed",
            "is_anchor": True,
            "completed": False,
            "status": "pending",
            "metadata": {
                "scheduled_start_time": "19:00"
            },
            "tags": ["meeting", "fixed"],
            "source": "seed",
            "created_at": datetime.now(timezone.utc),
        }
    ]
    await db.tasks.insert_many(sample_tasks)

    # ==========================================
    # 3. SEED LIFE MEMORY ("About You" Tab)
    # ==========================================
    print("Seeding Life Memories...")
    await db.memory_facts.delete_many({"source_event": "seed"})

    memories = [
        {
            "category": "people",
            "subject": "User",
            "predicate": "collaborates_with",
            "object": "Rahul — project partner and technical collaborator",
            "summary": "Rahul is collaborating on core system modules and reviews API designs.",
            "confidence": 0.98,
            "source_event": "seed",
            "tags": ["people", "work"],
            "created_at": datetime.now(timezone.utc),
        },
        {
            "category": "preferences",
            "subject": "User",
            "predicate": "work_routine",
            "object": "Strongest concentration occurs between 9:00 AM and 1:00 PM",
            "summary": "Prefers scheduling demanding architectural and coding tasks before afternoon meetings.",
            "confidence": 0.95,
            "source_event": "seed",
            "tags": ["preferences", "energy"],
            "created_at": datetime.now(timezone.utc),
        },
        {
            "category": "preferences",
            "subject": "User",
            "predicate": "workout_timing",
            "object": "Prefers evening workouts around 6:30 PM",
            "summary": "Workout blocks are usually scheduled post-work before dinner.",
            "confidence": 0.92,
            "source_event": "seed",
            "tags": ["preferences", "health"],
            "created_at": datetime.now(timezone.utc),
        },
        {
            "category": "goals",
            "subject": "User",
            "predicate": "weekly_target",
            "object": "Ship native mobile build and maintain 4 exercise sessions/week",
            "summary": "Current priority is finishing the Personal Life OS native client.",
            "confidence": 0.99,
            "source_event": "seed",
            "tags": ["goals"],
            "created_at": datetime.now(timezone.utc),
        },
        {
            "category": "routines",
            "subject": "User",
            "predicate": "sleep_target",
            "object": "Target bedtime is 11:30 PM for 7.5 hours of sleep",
            "summary": "Hard stop bedtime is anchored at 23:30 to avoid next-day cognitive depletion.",
            "confidence": 0.96,
            "source_event": "seed",
            "tags": ["health", "sleep"],
            "created_at": datetime.now(timezone.utc),
        }
    ]
    await db.memory_facts.insert_many(memories)

    # ==========================================
    # 4. SEED TODAY'S SCHEDULE (Schedule Tab)
    # ==========================================
    print("Seeding Today's Schedule...")
    initial_blocks = [
        {
            "start_time": "09:30",
            "end_time": "11:00",
            "title": "Deep Work: Core Engine Refactoring",
            "block_type": "deep_work",
            "category": "work",
            "action_notes": "Focused implementation without multitasking.",
            "elasticity": "flexible",
            "is_anchor": False,
            "energy_required": "high",
            "status_tag": "intact",
        },
        {
            "start_time": "11:00",
            "end_time": "11:30",
            "title": "Decompression & Coffee Break",
            "block_type": "recharge",
            "category": "health",
            "action_notes": "Hydrate and step away from screens.",
            "elasticity": "flexible",
            "is_anchor": False,
            "energy_required": "low",
            "status_tag": "intact",
        },
        {
            "start_time": "11:30",
            "end_time": "13:00",
            "title": "Mobile Client Integration",
            "block_type": "deep_work",
            "category": "work",
            "action_notes": "Connect React Native tabs to FastAPI endpoints.",
            "elasticity": "flexible",
            "is_anchor": False,
            "energy_required": "high",
            "status_tag": "intact",
        },
        {
            "start_time": "13:00",
            "end_time": "14:00",
            "title": "Lunch & Rest",
            "block_type": "recharge",
            "category": "routine",
            "action_notes": "Midday meal and reset.",
            "elasticity": "fixed",
            "is_anchor": True,
            "energy_required": "low",
            "status_tag": "intact",
        },
        {
            "start_time": "19:00",
            "end_time": "19:30",
            "title": "Evening Architecture Sync",
            "block_type": "deep_work",
            "category": "work",
            "action_notes": "Protected calendar anchor with project collaborators.",
            "elasticity": "fixed",
            "is_anchor": True,
            "energy_required": "medium",
            "status_tag": "intact",
        },
        {
            "start_time": "20:30",
            "end_time": "21:30",
            "title": "Dinner & Wind Down",
            "block_type": "recharge",
            "category": "routine",
            "action_notes": "Evening meal and relaxing.",
            "elasticity": "fixed",
            "is_anchor": False,
            "energy_required": "low",
            "status_tag": "intact",
        },
        {
            "start_time": "23:00",
            "end_time": "23:30",
            "title": "Prepare for Sleep",
            "block_type": "buffer",
            "category": "routine",
            "action_notes": "Hard stop before 23:30 bedtime.",
            "elasticity": "flexible",
            "is_anchor": False,
            "energy_required": "low",
            "status_tag": "intact",
        }
    ]

    schedule_doc = {
        "date": today_str,
        "current_time_anchor": "09:30",
        "last_replanned_at": datetime.now(timezone.utc),
        "summary": "Balanced schedule with protected morning focus sprints and 19:00 sync anchor.",
        "summary_verdict": "Balanced schedule with protected morning focus sprints and 19:00 sync anchor.",
        "triage_rationale": "Initial baseline schedule for testing.",
        "blocks": initial_blocks,
        "schedule": initial_blocks,
        "schedule_blocks": initial_blocks,
        "deferred_tasks": [],
        "vital_warnings": [],
    }

    await db.schedules.update_one(
        {"date": today_str},
        {"$set": schedule_doc},
        upsert=True
    )

    # Seed Causal Graph Edges
    print("Seeding Causal Graph Edges...")
    await db.graph_edges.delete_many({"source": {"$in": ["morning_headache", "low_physical_alertness", "cognitive_depletion", "high_friction", "short_chunking"]}})
    
    causal_edges = [
        {
            "source": "morning_headache",
            "target": "afternoon_brain_fog",
            "weight": 0.85,
            "occurrences": 12,
            "intervention_rule": "Limit deep focus sprints to 30 mins; schedule 20m decompression after.",
        },
        {
            "source": "cognitive_depletion",
            "target": "schedule_slip",
            "weight": 0.78,
            "occurrences": 15,
            "intervention_rule": "Postpone complex refactoring; prioritize quick communication tasks.",
        },
        {
            "source": "low_physical_alertness",
            "target": "monolithic_task_abandonment",
            "weight": 0.80,
            "occurrences": 9,
            "intervention_rule": "Do not schedule uninterrupted work blocks exceeding 45 minutes.",
        },
        {
            "source": "short_chunking",
            "target": "task_completion",
            "weight": 0.90,
            "occurrences": 24,
            "intervention_rule": "Keep tasks chunked under 25 minutes for steady momentum.",
        }
    ]
    await db.graph_edges.insert_many(causal_edges)

    print("\nSeed Complete! Database is populated with clean test data.")
    print("-----------------------------------------------------------------")
    print(f"• User State : deep_flow (Clarity: 9/10, Alertness: 8/10)")
    print(f"• Tasks      : {len(sample_tasks)} active tasks in queue")
    print(f"• Memories   : {len(memories)} facts in Life Memory")
    print(f"• Schedule   : {len(initial_blocks)} blocks scheduled for {today_str}")


if __name__ == "__main__":
    asyncio.run(seed_database())