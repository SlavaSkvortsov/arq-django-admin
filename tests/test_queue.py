import asyncio
from dataclasses import dataclass
from typing import AsyncGenerator, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from arq import ArqRedis
from arq.constants import default_queue_name
from arq.jobs import DeserializationError, Job, JobStatus, JobDef
from django.conf import settings

from arq_admin.queue import Queue, QueueStats
from tests.conftest import JobsCreator


@pytest_asyncio.fixture()
async def queue() -> AsyncGenerator[Queue, None]:
    async with Queue.from_name(default_queue_name) as queue:
        yield queue


@pytest.mark.asyncio()
@pytest.mark.usefixtures('all_jobs')
async def test_all_get_jobs(queue: Queue) -> None:
    jobs = await queue.get_jobs()
    assert len(jobs) == 4


@pytest.mark.asyncio()
@pytest.mark.usefixtures('all_jobs')
async def test_status_filter(queue: Queue) -> None:
    assert len(await queue.get_jobs(JobStatus.deferred)) == 1
    assert len(await queue.get_jobs(JobStatus.in_progress)) == 1
    assert len(await queue.get_jobs(JobStatus.queued)) == 1
    assert len(await queue.get_jobs(JobStatus.complete)) == 1


@pytest.mark.asyncio()
@pytest.mark.usefixtures('all_jobs')
async def test_stats(queue: Queue) -> None:
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
@pytest.mark.usefixtures('all_jobs')
async def test_stats_with_running_job_wo_zscore(redis: ArqRedis, queue: Queue) -> None:
    await redis.zrem(queue.name, 'running_task')

    assert await queue.get_stats() == QueueStats(
        name=default_queue_name,
        host=settings.REDIS_SETTINGS.host,
        port=settings.REDIS_SETTINGS.port,
        database=settings.REDIS_SETTINGS.database,
        queued_jobs=1,
        running_jobs=0,
        deferred_jobs=1,
    )


@pytest.mark.asyncio()
@pytest.mark.usefixtures('all_jobs')
async def test_stats_job_with_colon_in_the_name(redis: ArqRedis, queue: Queue) -> None:
    await redis.enqueue_job('new_task', _job_id='queued:task')

    assert await queue.get_stats() == QueueStats(
        name=default_queue_name,
        host=settings.REDIS_SETTINGS.host,
        port=settings.REDIS_SETTINGS.port,
        database=settings.REDIS_SETTINGS.database,
        queued_jobs=2,
        running_jobs=1,
        deferred_jobs=1,
    )


@pytest.mark.asyncio()
@patch.object(Queue, '_get_job_id_to_status_map')
async def test_stats_with_error(mocked_get_job_ids: AsyncMock, queue: Queue) -> None:
    error_text = 'test error'
    mocked_get_job_ids.side_effect = Exception(error_text)
    assert await queue.get_stats() == QueueStats(
        name=default_queue_name,
        host=settings.REDIS_SETTINGS.host,
        port=settings.REDIS_SETTINGS.port,
        database=settings.REDIS_SETTINGS.database,
        error=error_text,
    )


@pytest.mark.asyncio()
@patch.object(Job, 'info')
async def test_deserialize_error(mocked_job_info: MagicMock, jobs_creator: JobsCreator, queue: Queue) -> None:
    job = await jobs_creator.create_queued()
    mocked_job_info.side_effect = DeserializationError()
    job_info = await queue.get_job_by_id(job.job_id)
    assert job_info.function == "Unknown, can't deserialize"


@dataclass
class NewArqJobDef(JobDef):
    job_id: Optional[str]


@pytest.mark.asyncio()
@patch('arq_admin.queue.JobDef', NewArqJobDef)
@patch('arq_admin.queue.ARQ_VERSION_TUPLE', (0, 26, 0))
@patch.object(Job, 'info')
async def test_deserialize_error_in_arq_26(mocked_job_info: MagicMock, jobs_creator: JobsCreator, queue: Queue) -> None:
    job = await jobs_creator.create_queued()
    mocked_job_info.side_effect = DeserializationError()
    job_info = await queue.get_job_by_id(job.job_id)
    assert job_info.function == "Unknown, can't deserialize"


@pytest.mark.asyncio()
@patch.object(Job, 'abort')
@pytest.mark.parametrize('success', [True, False])
async def test_abort_job(mocked_abort: AsyncMock, jobs_creator: JobsCreator, success: bool, queue: Queue) -> None:
    mocked_abort.return_value = success
    job = await jobs_creator.create_queued()

    assert await queue.abort_job(job.job_id) is success


@pytest.mark.asyncio()
@patch.object(Job, 'abort')
async def test_abort_job_timeout(mocked_abort: AsyncMock, jobs_creator: JobsCreator, queue: Queue) -> None:
    mocked_abort.side_effect = asyncio.TimeoutError
    job = await jobs_creator.create_queued()
    assert await queue.abort_job(job.job_id) is None
