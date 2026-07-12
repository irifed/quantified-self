import argparse
import logging

from health_observatory.config import get_settings
from health_observatory.scheduler import run_intervals_sync, run_scheduler, run_withings_sync


def main() -> None:
    parser = argparse.ArgumentParser(description="Personal Health Observatory")
    parser.add_argument("command", choices=("scheduler", "sync"), nargs="?", default="scheduler")
    args = parser.parse_args()
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if args.command == "sync":
        run_withings_sync(settings)
        run_intervals_sync(settings)
    else:
        run_scheduler(settings)


if __name__ == "__main__":
    main()
