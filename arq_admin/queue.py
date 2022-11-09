import asyncio
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, List, Optional, Set

from arq import ArqRedis
from arq.connections import RedisSettings, create_pool
from arq.constants import result_key_prefix
from arq.jobs import DeserializationError, Job as ArqJob, JobDef, JobStatus
from django.utils import timezone

from arq_admin import settings
from arq_admin.job import JobInfo


@dataclass
class QueueStats:
    name: str
    host: str
    port: int
    database: int

    queued_jobs: Optional[int] = None
    running_jobs: Optional[int] = None
    deferred_jobs: Optional[int] = None

    error: Optional[str] = None


@dataclass
class Queue:
    redis_settings: RedisSettings
    name: str
    _redis: ArqRedis = field(init=False, default=None)  # type: ignore

    async def __aenter__(self) -> 'Queue':
        self._redis = await create_pool(self.redis_settings)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self._redis.close()

    @classmethod
    def from_name(cls, name: str) -> 'Queue':
        return cls(
            name=name,
            redis_settings=settings.ARQ_QUEUES[name],
        )

    async def get_jobs(self, status: Optional[JobStatus] = None) -> List[JobInfo]:
        job_ids = await self._get_job_ids()

        if status:
            job_ids_tuple = tuple(job_ids)
            statuses = await asyncio.gather(*[self._get_job_status(job_id) for job_id in job_ids_tuple])
            job_ids = {job_id for (job_id, job_status) in zip(job_ids_tuple, statuses) if job_status == status}

        jobs: List[JobInfo] = await asyncio.gather(*[self.get_job_by_id(job_id) for job_id in job_ids])

        return jobs

    async def get_stats(self) -> QueueStats:
        result = QueueStats(
            name=self.name,
            host=str(self.redis_settings.host),
            port=self.redis_settings.port,
            database=self.redis_settings.database,
        )
        try:
            job_ids = await self._get_job_ids()
            statuses = await asyncio.gather(*[self._get_job_status(job_id) for job_id in job_ids])
        except Exception as ex:  # noqa: B902
            result.error = str(ex)
        else:
            result.queued_jobs = len([status for status in statuses if status == JobStatus.queued])
            result.running_jobs = len([status for status in statuses if status == JobStatus.in_progress])
            result.deferred_jobs = len([status for status in statuses if status == JobStatus.deferred])

        return result

    async def get_job_by_id(self, job_id: str) -> JobInfo:
        arq_job = ArqJob(
            job_id=job_id,
            redis=self._redis,
            _queue_name=self.name,
            _deserializer=settings.ARQ_DESERIALIZER_BY_QUEUE.get(self.name),
        )

        unknown_function_msg = "Can't find job"
        base_info = None
        try:
            base_info = await arq_job.info()
        except DeserializationError:
            unknown_function_msg = "Unknown, can't deserialize"

        if not base_info:
            base_info = JobDef(
                function=unknown_function_msg,
                args=(),
                kwargs={},
                job_try=-1,
                enqueue_time=timezone.now().replace(year=2077),
                score=420,
            )

        job_info = JobInfo.from_base(base_info, job_id)
        job_info.status = await arq_job.status()

        return job_info

    async def abort_job(self, job_id: str) -> Optional[bool]:
        # None here means we are not sure if the job was aborted or not
        arq_job = ArqJob(
            job_id=job_id,
            redis=self._redis,
            _queue_name=self.name,
            _deserializer=settings.ARQ_DESERIALIZER_BY_QUEUE.get(self.name),
        )
        with suppress(asyncio.TimeoutError):
            return await arq_job.abort(timeout=settings.ARQ_JOB_ABORT_TIMEOUT)

        return None

    async def _get_job_status(self, job_id: str) -> JobStatus:
        arq_job = ArqJob(
            job_id=job_id,
            redis=self._redis,
            _queue_name=self.name,
            _deserializer=settings.ARQ_DESERIALIZER_BY_QUEUE.get(self.name),
        )
        return await arq_job.status()

    async def _get_job_ids(self) -> Set[str]:
        raw_job_ids = set(await self._redis.zrangebyscore(self.name, '-inf', 'inf'))
        result_keys = await self._redis.keys(f'{result_key_prefix}*')
        raw_job_ids |= {key[len(result_key_prefix):] for key in result_keys}

        return {job_id.decode('utf-8') if isinstance(job_id, bytes) else job_id for job_id in raw_job_ids}
