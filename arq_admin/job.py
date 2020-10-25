from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Union

from arq.jobs import JobDef, JobResult, JobStatus


@dataclass
class JobInfo(JobDef):
    job_id: str

    success: bool = False
    result: Optional[Any] = None
    start_time: Optional[datetime] = None
    finish_time: Optional[datetime] = None

    status: JobStatus = JobStatus.queued

    @classmethod
    def from_base(cls, base_info: Union[JobDef, JobResult], job_id: str) -> 'JobInfo':
        kwargs = {
            'function': base_info.function,
            'args': base_info.args,
            'kwargs': base_info.kwargs,
            'job_try': base_info.job_try,
            'enqueue_time': base_info.enqueue_time,
            'score': base_info.score,
            'job_id': job_id,
        }
        if isinstance(base_info, JobResult):
            kwargs.update({
                'success': base_info.success,
                'result': base_info.result,
                'start_time': base_info.start_time,
                'finish_time': base_info.finish_time,
            })

        return cls(**kwargs)  # type: ignore
