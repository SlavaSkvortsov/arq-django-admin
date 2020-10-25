from typing import List
from unittest.mock import MagicMock, patch

import pytest
from arq.constants import default_queue_name
from arq.jobs import DeserializationError, Job, JobStatus
from django.conf import settings

from arq_admin.queue import Queue, QueueStats
from arq_admin.tests.conftest import JobsCreator


@pytest.mark.asyncio
async def test_all_get_jobs(all_jobs: List[Job]) -> None:
    queue = Queue.from_name(default_queue_name)
    assert len(await queue.get_jobs()) == 5


@pytest.mark.asyncio
async def test_status_filter(all_jobs: List[Job]) -> None:
    queue = Queue.from_name(default_queue_name)
    assert len(await queue.get_jobs(JobStatus.deferred)) == 1
    assert len(await queue.get_jobs(JobStatus.complete)) == 2
    assert len(await queue.get_jobs(JobStatus.in_progress)) == 1
    assert len(await queue.get_jobs(JobStatus.queued)) == 1


@pytest.mark.asyncio
async def test_stats(all_jobs: List[Job]) -> None:
    queue = Queue.from_name(default_queue_name)
    oldest_job = min([(await job.info()).enqueue_time for job in all_jobs])  # type: ignore  # noqa: C407
    assert await queue.get_stats() == QueueStats(
        name=default_queue_name,
        oldest_job=oldest_job,
        host=settings.REDIS_SETTINGS.host,
        port=settings.REDIS_SETTINGS.port,
        database=settings.REDIS_SETTINGS.database,
        queued_jobs=1,
        successful_jobs=1,
        failed_jobs=1,
        running_jobs=1,
        deferred_jobs=1,
    )


@pytest.mark.asyncio
@patch.object(Job, 'info')
async def test_deserialize_error(mocked_job_info: MagicMock, jobs_creator: JobsCreator) -> None:
    job = await jobs_creator.create_successful()
    mocked_job_info.side_effect = DeserializationError()
    queue = Queue.from_name(default_queue_name)
    job_info = await queue.get_job_by_id(job.job_id)
    assert job_info.function == "Unknown, can't deserialize"
