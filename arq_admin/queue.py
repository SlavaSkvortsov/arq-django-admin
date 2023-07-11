import asyncio
import re
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from arq import ArqRedis
from arq.connections import RedisSettings, create_pool
from arq.jobs import DeserializationError, Job as ArqJob, JobDef, JobStatus
from arq.utils import timestamp_ms
from django.utils import timezone

from arq_admin import settings
from arq_admin.job import JobInfo

ARQ_PREFIX = 'arq:'
ARQ_KEY_REGEX = re.compile(r'arq\:(?P<prefix>.+?)\:(?P<job_id>.+)')
PREFIX_PRIORITY = {prefix: i for i, prefix in enumerate(['job', 'in-progress', 'result'])}


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
    concurrent_redis_access_sem: asyncio.Semaphore = field(
        default_factory=lambda: asyncio.Semaphore(settings.ARQ_MAX_CONNECTIONS),
    )
    _cached_job_id_to_status_map: Optional[Dict[str, JobStatus]] = None
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
        job_id_to_status_map = await self._get_job_id_to_status_map()

        if status:
            job_ids = {job_id for (job_id, job_status) in job_id_to_status_map.items() if job_status == status}
        else:
            job_ids = set(job_id_to_status_map.keys())

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
            job_id_to_status_map = await self._get_job_id_to_status_map()
        except Exception as ex:  # noqa: B902
            result.error = str(ex)
        else:
            statuses = job_id_to_status_map.values()

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
        async with self.concurrent_redis_access_sem:
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
        job_info.status = await self._get_job_status(job_id)

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
        if self._cached_job_id_to_status_map is not None:
            return self._cached_job_id_to_status_map.get(job_id, JobStatus.not_found)

        arq_job = ArqJob(
            job_id=job_id,
            redis=self._redis,
            _queue_name=self.name,
            _deserializer=settings.ARQ_DESERIALIZER_BY_QUEUE.get(self.name),
        )
        async with self.concurrent_redis_access_sem:
            return await arq_job.status()

    async def _get_job_id_to_status_map(self) -> Dict[str, JobStatus]:
        if self._cached_job_id_to_status_map is not None:
            return self._cached_job_id_to_status_map

        async with self._redis.pipeline(transaction=True) as pipe:
            await pipe.keys(f'{ARQ_PREFIX}*:*')
            await pipe.zrange(self.name, withscores=True, start=0, end=-1)
            all_arq_keys, job_ids_with_scores = await pipe.execute()

        regex_matches_from_arq_keys = (ARQ_KEY_REGEX.match(key.decode('utf-8')) for key in all_arq_keys)
        # iter over dicts with job ids and their keys' prefixes
        # can't create mapping from ids to prefixes right away here
        # because we can have multiple keys with different prefixes for one job and need to use the more specific one
        job_ids_with_prefixes = (match.groupdict() for match in regex_matches_from_arq_keys if match is not None)

        job_ids_to_scores = {key[0].decode('utf-8'): key[1] for key in job_ids_with_scores}
        job_ids_to_prefixes = dict(sorted(
            # not only ensure that we don't get key error but also filter out stuff that's not a client job
            ([key['job_id'], key['prefix']] for key in job_ids_with_prefixes if key['prefix'] in PREFIX_PRIORITY),
            # make sure that more specific indices go after less specific ones
            key=lambda job_id_with_prefix: PREFIX_PRIORITY[job_id_with_prefix[-1]],
        ))

        self._cached_job_id_to_status_map = {
            job_id: self._get_job_status_from_raw_data(prefix, job_ids_to_scores.get(job_id))
            for job_id, prefix in job_ids_to_prefixes.items()
        }

        return self._cached_job_id_to_status_map

    def _get_job_status_from_raw_data(self, prefix: str, zscore: Optional[int]) -> JobStatus:  # noqa: CFQ004
        if prefix == 'result':
            return JobStatus.complete
        if prefix == 'in-progress' and zscore:
            return JobStatus.in_progress
        if zscore:
            return JobStatus.deferred if zscore > timestamp_ms() else JobStatus.queued
        return JobStatus.not_found
