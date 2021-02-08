import asyncio
from dataclasses import dataclass
from typing import List, NamedTuple, Optional

from arq import ArqRedis
from arq.connections import RedisSettings, create_pool
from arq.constants import result_key_prefix
from arq.jobs import DeserializationError, Job as ArqJob, JobDef, JobStatus
from django.utils import timezone

from arq_admin import settings
from arq_admin.job import JobInfo


class QueueStats(NamedTuple):
    name: str
    host: str
    port: int
    database: int

    queued_jobs: int
    complete_jobs: int
    running_jobs: int
    deferred_jobs: int


@dataclass
class Queue:
    redis_settings: RedisSettings
    name: str

    @classmethod
    def from_name(cls, name: str) -> 'Queue':
        return cls(
            name=name,
            redis_settings=settings.ARQ_QUEUES[name],
        )

    async def get_jobs(self, status: Optional[JobStatus] = None) -> List[JobInfo]:
        redis = await create_pool(self.redis_settings)
        job_ids = set(await redis.zrangebyscore(self.name))
        result_keys = await redis.keys(f'{result_key_prefix}*')
        job_ids |= {key[len(result_key_prefix):] for key in result_keys}

        if status:
            job_ids_tuple = tuple(job_ids)
            statuses = await asyncio.gather(*[self._get_job_status(job_id, redis) for job_id in job_ids_tuple])
            job_ids = {job_id for (job_id, job_status) in zip(job_ids_tuple, statuses) if job_status == status}

        jobs: List[JobInfo] = await asyncio.gather(*[self.get_job_by_id(job_id, redis) for job_id in job_ids])

        redis.close()
        await redis.wait_closed()

        return jobs

    async def get_stats(self) -> QueueStats:
        redis = await create_pool(self.redis_settings)
        job_ids = set(await redis.zrangebyscore(self.name))
        result_keys = await redis.keys(f'{result_key_prefix}*')
        job_ids |= {key[len(result_key_prefix):] for key in result_keys}

        statuses = await asyncio.gather(*[self._get_job_status(job_id, redis) for job_id in job_ids])

        return QueueStats(
            name=self.name,
            host=str(self.redis_settings.host),
            port=self.redis_settings.port,
            database=self.redis_settings.database,
            queued_jobs=len([status for status in statuses if status == JobStatus.queued]),
            complete_jobs=len([status for status in statuses if status == JobStatus.complete]),
            running_jobs=len([status for status in statuses if status == JobStatus.in_progress]),
            deferred_jobs=len([status for status in statuses if status == JobStatus.deferred]),
        )

    async def get_job_by_id(self, job_id: str, redis: Optional[ArqRedis] = None) -> JobInfo:
        close_redis = False
        if redis is None:
            redis = await create_pool(self.redis_settings)
            close_redis = True

        arq_job = ArqJob(
            job_id=job_id,
            redis=redis,
            _queue_name=self.name,
            _deserializer=settings.ARQ_DESERIALIZER,
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

        if close_redis:
            redis.close()
            await redis.wait_closed()

        return job_info

    async def _get_job_status(self, job_id: str, redis: ArqRedis) -> JobStatus:
        arq_job = ArqJob(
            job_id=job_id,
            redis=redis,
            _queue_name=self.name,
            _deserializer=settings.ARQ_DESERIALIZER,
        )
        return await arq_job.status()
