import asyncio
from operator import attrgetter
from typing import Any, Dict, List, Optional

from arq.jobs import JobStatus
from django.contrib import admin, messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, ListView

from arq_admin.job import JobInfo
from arq_admin.queue import Queue, QueueStats
from arq_admin.settings import ARQ_QUEUES


@method_decorator(staff_member_required, name='dispatch')
class QueueListView(ListView):
    template_name = 'arq_admin/queues.html'

    def get_queryset(self) -> List[QueueStats]:
        result = asyncio.run(self._gather_queues())
        return result

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(admin.site.each_context(self.request))

        return context

    @staticmethod
    async def _get_queue_stats(queue_name: str) -> QueueStats:
        async with Queue.from_name(queue_name) as queue:
            return await queue.get_stats()

    @classmethod
    async def _gather_queues(cls) -> List[QueueStats]:
        result = []  # pragma: no cover
        for name in ARQ_QUEUES.keys():  # pragma: no cover
            result.append(await cls._get_queue_stats(name))
        return result


@method_decorator(staff_member_required, name='dispatch')
class BaseJobListView(ListView):
    paginate_by = 100
    template_name = 'arq_admin/jobs.html'

    status: Optional[JobStatus] = None
    job_status_label: Optional[str] = None

    @property
    def job_status(self) -> str:
        if self.job_status_label:
            return self.job_status_label

        return self.status.value.capitalize() if self.status else 'Unknown'

    def get_queryset(self) -> List[JobInfo]:
        queue_name = self.kwargs['queue_name']  # pragma: no cover
        jobs = asyncio.run(self._get_queue_jobs(queue_name))
        return sorted(jobs, key=attrgetter('enqueue_time'))

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({
            **admin.site.each_context(self.request),
            'queue_name': self.kwargs['queue_name'],
            'job_status': self.job_status,
        })

        return context

    async def _get_queue_jobs(self, queue_name: str) -> List[JobInfo]:
        async with Queue.from_name(queue_name) as queue:
            return await queue.get_jobs(status=self.status)


class AllJobListView(BaseJobListView):
    job_status_label = 'All'


class QueuedJobListView(BaseJobListView):
    status = JobStatus.queued


class RunningJobListView(BaseJobListView):
    status = JobStatus.in_progress


class DeferredJobListView(BaseJobListView):
    status = JobStatus.deferred


class JobDetailView(DetailView):
    template_name = 'arq_admin/job_detail.html'

    def get_object(self, queryset: Optional[Any] = None) -> JobInfo:
        return asyncio.run(self._get_job_info())

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['queue_name'] = self.kwargs['queue_name']

        return context

    async def _get_job_info(self) -> JobInfo:
        async with Queue.from_name(self.kwargs['queue_name']) as queue:
            return await queue.get_job_by_id(self.kwargs['job_id'])


class JobAbortView(JobDetailView):
    template_name = 'arq_admin/job_abort.html'

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:  # pragma: nocover
        aborted = asyncio.run(self._abort_job())
        if aborted:
            messages.success(request, 'Job aborted successfully')
        elif aborted is None:
            messages.warning(request, 'An issue happened while aborting the job, but it may be aborted anyway')
        else:
            messages.error(request, 'Job was not aborted')

        return redirect('arq_admin:job_detail', queue_name=self.kwargs['queue_name'], job_id=self.kwargs['job_id'])

    async def _abort_job(self) -> Optional[bool]:
        async with Queue.from_name(self.kwargs['queue_name']) as queue:
            return await queue.abort_job(self.kwargs['job_id'])
