import pytest

from health_observatory import scheduler
from health_observatory.config import Settings
from health_observatory.sync.withings import WithingsApiError


def test_scheduler_starts_when_withings_initial_sync_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    class FakeScheduler:
        def __init__(self, timezone: object) -> None:
            pass

        def add_job(self, func: object, *args: object, **kwargs: object) -> None:
            calls.append("job")

        def start(self) -> None:
            calls.append("start")

    def fail_withings(settings: Settings) -> None:
        calls.append("withings")
        raise WithingsApiError("expired token")

    def run_intervals(settings: Settings) -> None:
        calls.append("intervals")

    monkeypatch.setattr(scheduler, "BlockingScheduler", FakeScheduler)
    monkeypatch.setattr(scheduler, "run_withings_sync", fail_withings)
    monkeypatch.setattr(scheduler, "run_intervals_sync", run_intervals)

    scheduler.run_scheduler(Settings(_env_file=None))

    assert calls == ["job", "job", "withings", "intervals", "start"]
