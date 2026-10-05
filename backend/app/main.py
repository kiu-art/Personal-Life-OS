from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Database lifecycle functions
from app.core.database import connect_to_mongo, close_mongo_connection  # or disconnect_from_mongo
from app.routers import observations, recommendations, schedule, memory, story, lifemap, review, tasks

from contextlib import asynccontextmanager
from app.services.scheduler_cron import start_system_schedulers

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize MongoDB client
    print("Connecting to MongoDB...")
    await connect_to_mongo()
    start_system_schedulers()
    print(" Connected to MongoDB successfully.")
    
    yield  # Application runs while yielded
    
    # Shutdown: Close database connection pools
    print("Closing MongoDB connection...")
    try:
        await close_mongo_connection()
    except Exception:
        pass


app = FastAPI(
    title="Personal Life OS Backend",
    lifespan=lifespan,
)

# CORS configuration (useful for React Native / Web)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(observations.router)
app.include_router(recommendations.router)
app.include_router(schedule.router)
app.include_router(memory.router)
app.include_router(story.router)
app.include_router(lifemap.router)
app.include_router(review.router)
app.include_router(tasks.router)


@app.get("/health")
async def health_check():
    return {"status": "online"}

