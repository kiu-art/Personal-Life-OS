import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger("uvicorn.error")


class DatabaseManager:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None


db_manager = DatabaseManager()


async def connect_to_mongo() -> None:
    """Initializes the MongoDB connection pool and verifies access via a ping."""
    try:
        logger.info("Connecting to MongoDB Atlas...")
        db_manager.client = AsyncIOMotorClient(
            settings.MONGO_URI,
            maxPoolSize=10,
            minPoolSize=1,
            serverSelectionTimeoutMS=5000,
        )
        db_manager.db = db_manager.client[settings.DB_NAME]

        # Verify cluster ping
        await db_manager.client.admin.command("ping")
        logger.info(f"Connected to MongoDB Atlas database: '{settings.DB_NAME}'")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB Atlas: {e}")
        raise e


async def close_mongo_connection() -> None:
    """Closes all active MongoDB connection pools."""
    if db_manager.client:
        logger.info("Closing MongoDB connection pool...")
        db_manager.client.close()
        logger.info("MongoDB connection closed.")


def get_database() -> AsyncIOMotorDatabase:
    """Dependency helper to access the active database instance."""
    if db_manager.db is None:
        raise RuntimeError("Database client is not initialized. Call connect_to_mongo() first.")
    return db_manager.db