import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arq.constants import default_queue_name
from arq.jobs import DeserializationError, Job, JobStatus
from django.conf import settings

from arq_admin.queue import Queue, QueueStats
from tests.conftest import JobsCreator


@pytest.mark.asyncio()
@pytest.mark.usefixtures('all_jobs')
async def test_all_get_jobs() -> None:
    queue = Queue.from_name(default_queue_name)
    jobs = await queue.get_jobs()
    assert len(jobs) == 4


@pytest.mark.asyncio()
@pytest.mark.usefixtures('all_jobs')
async def test_status_filter() -> None:
    queue = Queue.from_name(default_queue_name)
    assert len(await queue.get_jobs(JobStatus.deferred)) == 1
    assert len(await queue.get_jobs(JobStatus.in_progress)) == 1
    assert len(await queue.get_jobs(JobStatus.queued)) == 1
    assert len(await queue.get_jobs(JobStatus.complete)) == 1


@pytest.mark.asyncio()
@pytest.mark.usefixtures('all_jobs')
async def test_stats() -> None:
    queue = Queue.from_name(default_queue_name)
    assert await queue.get_stats() == QueueStats(
        name=default_queue_name,
        host=settings.REDIS_SETTINGS.host,
        port=settings.REDIS_SETTINGS.port,
        database=settings.REDIS_SETTINGS.database,
        queued_jobs=1,
        running_jobs=1,
        deferred_jobs=1,
    )


@pytest.mark.asyncio()
@patch.object(Queue, '_get_job_ids')
async def test_stats_with_error(mocked_get_job_ids: AsyncMock) -> None:
    error_text = 'test error'
    mocked_get_job_ids.side_effect = Exception(error_text)
    queue = Queue.from_name(default_queue_name)
    assert await queue.get_stats() == QueueStats(
        name=default_queue_name,
        host=settings.REDIS_SETTINGS.host,
        port=settings.REDIS_SETTINGS.port,
        database=settings.REDIS_SETTINGS.database,
        error=error_text,
    )


@pytest.mark.asyncio()
@patch.object(Job, 'info')
async def test_deserialize_error(mocked_job_info: MagicMock, jobs_creator: JobsCreator) -> None:
    job = await jobs_creator.create_queued()
    mocked_job_info.side_effect = DeserializationError()
    queue = Queue.from_name(default_queue_name)
    job_info = await queue.get_job_by_id(job.job_id)
    assert job_info.function == "Unknown, can't deserialize"


@pytest.mark.asyncio()
@patch.object(Job, 'abort')
@pytest.mark.parametrize('success', [True, False])
async def test_abort_job(mocked_abort: AsyncMock, jobs_creator: JobsCreator, success: bool) -> None:
    mocked_abort.return_value = success
    job = await jobs_creator.create_queued()
    queue = Queue.from_name(default_queue_name)

    assert await queue.abort_job(job.job_id) is success


@pytest.mark.asyncio()
@patch.object(Job, 'abort')
async def test_abort_job_timeout(mocked_abort: AsyncMock, jobs_creator: JobsCreator) -> None:
    mocked_abort.side_effect = asyncio.TimeoutError
    job = await jobs_creator.create_queued()
    queue = Queue.from_name(default_queue_name)
    assert await queue.abort_job(job.job_id) is None
