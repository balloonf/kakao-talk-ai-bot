from __future__ import annotations

import logging

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import DATA_DIR, TIMEZONE
from app.summarizer import run_daily_summary

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def create_scheduler() -> AsyncIOScheduler:
    db_path = DATA_DIR / "scheduler.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    jobstores = {"default": SQLAlchemyJobStore(url=f"sqlite:///{db_path}")}
    scheduler = AsyncIOScheduler(jobstores=jobstores, timezone=TIMEZONE)

    scheduler.add_job(
        run_daily_summary,
        trigger="cron",
        hour=0,
        minute=0,
        id="daily_summary",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    return scheduler


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = create_scheduler()
    return _scheduler
