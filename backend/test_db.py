import asyncio
from app.core.database import connect_to_mongo, close_mongo_connection, get_database


async def main():
    print("Testing connection to MongoDB Atlas...")
    await connect_to_mongo()
    db = get_database()
    collections = await db.list_collection_names()
    print(f"Existing collections in '{db.name}': {collections}")
    await close_mongo_connection()
    print("Database connection test passed.")


if __name__ == "__main__":
    asyncio.run(main())