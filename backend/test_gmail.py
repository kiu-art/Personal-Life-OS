import asyncio
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.workers.gmail_worker import gmail_worker


async def main():
    print("Connecting to MongoDB Atlas...")
    await connect_to_mongo()

    print("Checking Gmail for unread emails and running LangChain extraction...")
    await gmail_worker.run_once()

    db = get_database()
    tasks_count = await db.tasks.count_documents({})
    obs_count = await db.raw_observations.count_documents({})

    print(f"\nVerification Results:")
    print(f"- Total Raw Observations: {obs_count}")
    print(f"- Total Tasks in Database: {tasks_count}")

    latest_task = await db.tasks.find_one(sort=[("created_at", -1)])
    if latest_task:
        print(f"\nMost recent extracted task:")
        print(f"Title: {latest_task.get('title')}")
        print(f"Deadline: {latest_task.get('deadline')}")
        print(f"Elasticity: {latest_task.get('elasticity')}")
        print(f"Estimated Minutes: {latest_task.get('estimated_minutes')}")

    await close_mongo_connection()
    print("\nGmail test completed.")


if __name__ == "__main__":
    asyncio.run(main())