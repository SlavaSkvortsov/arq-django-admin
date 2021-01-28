import asyncio

import pytest
from arq import create_pool
from arq.constants import default_queue_name, result_key_prefix
from django.conf import settings
from django.contrib.auth.models import User
from django.template.response import TemplateResponse
from django.test import TestCase
from django.urls import reverse


class TestView(TestCase):

    def setUp(self) -> None:
        password = 'admin'
        admin_user: User = User.objects.create_superuser('admin', 'admin@admin.com', password)
        self.client.login(username=admin_user.username, password=password)

    def tearDown(self) -> None:
        User.objects.all().delete()

    def test_queues_view(self) -> None:
        url = reverse('arq_admin:home')
        result = self.client.get(url)
        assert isinstance(result, TemplateResponse)
        assert len(result.context_data['object_list']) == 1

    @pytest.mark.usefixtures('all_jobs')
    def test_all_queue_jobs_view(self) -> None:
        url = reverse('arq_admin:all_jobs', kwargs={'queue_name': default_queue_name})

        result = self.client.get(url)
        assert isinstance(result, TemplateResponse)
        assert len(result.context_data['object_list']) == 5

    @pytest.mark.usefixtures('all_jobs')
    @pytest.mark.usefixtures('unserializable_job')
    def test_all_queue_jobs_view_with_unserializable(self) -> None:
        url = reverse('arq_admin:all_jobs', kwargs={'queue_name': default_queue_name})

        result = self.client.get(url)
        assert isinstance(result, TemplateResponse)
        assert len(result.context_data['object_list']) == 6

    @pytest.mark.usefixtures('all_jobs')
    def test_successful_queue_jobs_view(self) -> None:
        url = reverse('arq_admin:successful_jobs', kwargs={'queue_name': default_queue_name})

        result = self.client.get(url)
        assert isinstance(result, TemplateResponse)
        assert len(result.context_data['object_list']) == 1

    @pytest.mark.usefixtures('all_jobs')
    def test_queued_queue_jobs_view(self) -> None:
        url = reverse('arq_admin:queued_jobs', kwargs={'queue_name': default_queue_name})

        result = self.client.get(url)
        assert isinstance(result, TemplateResponse)
        assert len(result.context_data['object_list']) == 1

    @pytest.mark.usefixtures('all_jobs')
    def test_failed_queue_jobs_view(self) -> None:
        url = reverse('arq_admin:failed_jobs', kwargs={'queue_name': default_queue_name})

        result = self.client.get(url)
        assert isinstance(result, TemplateResponse)
        assert len(result.context_data['object_list']) == 1

    @pytest.mark.usefixtures('all_jobs')
    def test_running_queue_jobs_view(self) -> None:
        url = reverse('arq_admin:running_jobs', kwargs={'queue_name': default_queue_name})

        result = self.client.get(url)
        assert isinstance(result, TemplateResponse)
        assert len(result.context_data['object_list']) == 1

    @pytest.mark.usefixtures('all_jobs')
    def test_deferred_queue_jobs_view(self) -> None:
        url = reverse('arq_admin:deferred_jobs', kwargs={'queue_name': default_queue_name})

        result = self.client.get(url)
        assert isinstance(result, TemplateResponse)
        assert len(result.context_data['object_list']) == 1

    @pytest.mark.usefixtures('all_jobs')
    def test_job_detail_view(self) -> None:
        job_id = asyncio.run(self._get_job_id())
        url = reverse('arq_admin:job_detail', kwargs={'queue_name': default_queue_name, 'job_id': job_id})

        result = self.client.get(url)
        assert isinstance(result, TemplateResponse)
        assert result.context_data['object'].job_id == job_id

    @staticmethod
    async def _get_job_id() -> str:
        redis = await create_pool(settings.REDIS_SETTINGS)
        keys = await redis.keys(result_key_prefix + '*')

        redis.close()
        await redis.wait_closed()
        return keys[0][len(result_key_prefix):]
