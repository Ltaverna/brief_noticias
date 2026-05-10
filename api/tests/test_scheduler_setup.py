import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from noticias_api.config import Settings
from noticias_api.scheduler import setup_scheduler


def make_settings(**overrides) -> Settings:
    base = dict(
        database_url="postgresql+psycopg://x:x@h:5432/d",
        openai_api_key="sk-x",
    )
    base.update(overrides)
    return Settings(**base)


def test_default_one_job_for_cron_hour():
    s = make_settings()
    sched = setup_scheduler(s)
    jobs = sched.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "daily_briefing_07"


def test_multiple_jobs_when_cron_hours_set():
    s = make_settings(cron_hours="7,13,20")
    sched = setup_scheduler(s)
    jobs = sched.get_jobs()
    assert len(jobs) == 3
    ids = {j.id for j in jobs}
    assert ids == {"daily_briefing_07", "daily_briefing_13", "daily_briefing_20"}


def test_cron_hours_invalid_values_filtered():
    s = make_settings(cron_hours="7, 99, abc, 20")
    assert s.cron_hours_list == [7, 20]


def test_cron_hours_empty_falls_back_to_cron_hour():
    s = make_settings(cron_hours="", cron_hour=15)
    assert s.cron_hours_list == [15]
