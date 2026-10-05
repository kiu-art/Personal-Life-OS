import asyncio
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.review_engine import weekly_review_engine
from app.routers.story import generate_daily_story
from app.services.lifemap_engine import lifemap_engine

scheduler = AsyncIOScheduler()


async def nightly_maintenance_job():
    """Runs at 23:45 every night: Generates daily story and updates Life Map causal graph."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"[CRON] Running nightly synthesis for {today_str}...")
    try:
        await generate_daily_story(target_date=today_str)
        await lifemap_engine.learn_from_day(today_str)
        print(f"[CRON] Daily story and Life Map updated for {today_str}.")
    except Exception as e:
        print(f"[CRON ERROR] Nightly maintenance failed: {e}")


async def sunday_weekly_review_job():
    """Runs every Sunday at 23:55: Analyzes 7 days and saves the Weekly Review."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"[CRON] Running Sunday weekly review synthesis ending {today_str}...")
    try:
        await weekly_review_engine.generate_weekly_review(end_date_str=today_str)
        print(f"[CRON] Weekly review generated successfully.")
    except Exception as e:
        print(f"[CRON ERROR] Weekly review job failed: {e}")


def start_system_schedulers():
    # Every night at 11:45 PM
    scheduler.add_job(nightly_maintenance_job, CronTrigger(hour=23, minute=45))
    # Every Sunday at 11:55 PM
    scheduler.add_job(sunday_weekly_review_job, CronTrigger(day_of_week="sun", hour=23, minute=55))
    scheduler.start()