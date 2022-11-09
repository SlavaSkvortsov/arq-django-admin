import asyncio
from contextlib import suppress
from dataclasses import dataclass
from typing import (
    Any, AsyncGenerator, Callable, List, Optional, Sequence, Union,
)

import pytest
import pytest_asyncio
from arq import ArqRedis, Worker, create_pool
from arq.constants import job_key_prefix
from arq.jobs import Job, JobStatus
from arq.typing import WorkerCoroutine
from arq.worker import Function
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from django.test import AsyncClient

from tests.settings import REDIS_SETTINGS


@pytest_asyncio.fixture(autouse=True)
async def redis() -> AsyncGenerator[ArqRedis, None]:
    client = await create_pool(REDIS_SETTINGS)
    await client.flushall()
    yield client
    await client.flushall()
    await client.close()


@pytest_asyncio.fixture()
async def create_worker(redis: ArqRedis) -> AsyncGenerator[Callable[[Any], Worker], None]:
    worker: Optional[Worker] = None

    def create(functions: Sequence[Union[Function, WorkerCoroutine]], **kwargs: Any) -> Worker:
        nonlocal worker
        worker = Worker(
            functions=functions,
            redis_pool=redis,
            burst=True,
            max_burst_jobs=100,
            poll_delay=0,
            **kwargs,
        )
        return worker

    yield create

    if worker:
        await worker.close()


async def deferred_task(_ctx: Any) -> None:
    pass


async def running_task(_ctx: Any) -> None:
    await asyncio.sleep(0.5)


async def successful_task(_ctx: Any) -> str:
    return 'success'


async def failed_task(_ctx: Any) -> None:
    raise Exception


@dataclass
class JobsCreator:
    worker: Worker
    redis: ArqRedis

    async def create_queued(self) -> Job:
        job = await self.redis.enqueue_job('successful_task', _job_id='queued_task')
        assert job
        return job

    async def create_finished(self) -> Job:
        job = await self.redis.enqueue_job('successful_task', _job_id='finished_task')
        assert job
        await self.worker.main()

        return job

    async def create_running(self) -> Optional[Job]:
        job = await self.redis.enqueue_job('running_task', _job_id='running_task')
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(self.worker.main(), 0.1)

        return job

    async def create_deferred(self) -> Job:
        job = await self.redis.enqueue_job('deferred_task', _defer_by=9000, _job_id='deferred_task')
        assert job
        return job

    async def create_unserializable(self) -> Job:
        job = await self.redis.enqueue_job('successful_task', _job_id='unserializable_task')
        assert job
        await self.redis.set(job_key_prefix + job.job_id, 'RANDOM TEXT')
        return job


@pytest_asyncio.fixture()
async def jobs_creator(redis: ArqRedis, create_worker: Any) -> JobsCreator:
    worker = create_worker(functions=[deferred_task, running_task, successful_task, failed_task])
    return JobsCreator(worker=worker, redis=redis)


@pytest_asyncio.fixture()
async def all_jobs(jobs_creator: JobsCreator) -> List[Job]:
    while True:
        finished_job = await jobs_creator.create_finished()
        running_job = await jobs_creator.create_running()
        if not running_job:
            continue

        if (await running_job.status()) == JobStatus.in_progress:
            break

        await jobs_creator.redis.flushdb()

    return [
        finished_job,
        running_job,
        await jobs_creator.create_deferred(),
        await jobs_creator.create_queued(),
    ]


@pytest_asyncio.fixture()
async def unserializable_job(jobs_creator: JobsCreator) -> Job:
    return await jobs_creator.create_unserializable()


@pytest_asyncio.fixture()
@pytest.mark.django_db()
async def django_login(async_client: AsyncClient) -> AsyncGenerator[None, None]:
    password = 'admin'
    admin_user: User = await sync_to_async(User.objects.create_superuser)('admin', 'admin@admin.com', password)
    await sync_to_async(async_client.login)(username=admin_user.username, password=password)

    yield

    await sync_to_async(User.objects.all().delete)()
