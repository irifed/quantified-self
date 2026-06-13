import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from health_observatory.config import Settings
from health_observatory.db import session_scope
from health_observatory.sync.withings import WithingsClient, sync_withings

logger = logging.getLogger(__name__)


def run_withings_sync(settings: Settings) -> None:
    with WithingsClient(settings) as client, session_scope() as session:
        count = sync_withings(session, settings, client)
    logger.info("Withings sync completed: %s measure groups processed", count)


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
    run_withings_sync(settings)
    scheduler.start()
