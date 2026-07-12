import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from health_observatory.config import Settings
from health_observatory.db import session_scope
from health_observatory.sync.intervals import IntervalsClient, sync_intervals
from health_observatory.sync.withings import WithingsClient, sync_withings

logger = logging.getLogger(__name__)


def run_withings_sync(settings: Settings) -> None:
    with WithingsClient(settings) as client, session_scope() as session:
        count = sync_withings(session, settings, client)
    logger.info("Withings sync completed: %s measure groups processed", count)


def run_intervals_sync(settings: Settings) -> None:
    if not settings.intervals_configured:
        logger.info("intervals.icu sync skipped: INTERVALS_API_KEY is not configured")
        return
    with IntervalsClient(settings) as client, session_scope() as session:
        counts = sync_intervals(session, settings, client)
    logger.info(
        "intervals.icu sync completed: %s recovery rows, %s workouts processed",
        counts["daily_recovery"],
        counts["workouts"],
    )


def run_scheduler(settings: Settings) -> None:
    scheduler = BlockingScheduler(timezone=settings.tzinfo)
    scheduler.add_job(
        run_withings_sync,
        "interval",
        hours=settings.sync_interval_hours,
        args=[settings],
        id="withings-sync",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        run_intervals_sync,
        "interval",
        hours=settings.sync_interval_hours,
        args=[settings],
        id="intervals-sync",
        max_instances=1,
        coalesce=True,
    )
    run_withings_sync(settings)
    run_intervals_sync(settings)
    scheduler.start()
