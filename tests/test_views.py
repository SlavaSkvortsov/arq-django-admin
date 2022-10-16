from unittest.mock import AsyncMock, patch

import pytest
from arq import ArqRedis
from arq.constants import default_queue_name, job_key_prefix
from django.contrib.messages import get_messages
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.test import AsyncClient
from django.urls import reverse

from arq_admin.queue import Queue


@pytest.mark.asyncio()
@pytest.mark.django_db()
@pytest.mark.usefixtures('django_login')
async def test_queues_view(async_client: AsyncClient) -> None:
    url = reverse('arq_admin:home')
    result = await async_client.get(url)
    assert isinstance(result, TemplateResponse)
    assert len(result.context_data['object_list']) == 1


@pytest.mark.asyncio()
@pytest.mark.django_db()
@pytest.mark.usefixtures('django_login', 'all_jobs')
async def test_all_queue_jobs_view(async_client: AsyncClient) -> None:
    url = reverse('arq_admin:all_jobs', kwargs={'queue_name': default_queue_name})

    result = await async_client.get(url)
    assert isinstance(result, TemplateResponse)
    assert len(result.context_data['object_list']) == 4


@pytest.mark.asyncio()
@pytest.mark.django_db()
@pytest.mark.usefixtures('django_login', 'all_jobs', 'unserializable_job')
async def test_all_queue_jobs_view_with_unserializable(async_client: AsyncClient) -> None:
    url = reverse('arq_admin:all_jobs', kwargs={'queue_name': default_queue_name})

    result = await async_client.get(url)
    assert isinstance(result, TemplateResponse)
    assert len(result.context_data['object_list']) == 5


@pytest.mark.asyncio()
@pytest.mark.django_db()
@pytest.mark.usefixtures('django_login', 'all_jobs')
async def test_queued_queue_jobs_view(async_client: AsyncClient) -> None:
    url = reverse('arq_admin:queued_jobs', kwargs={'queue_name': default_queue_name})

    result = await async_client.get(url)
    assert isinstance(result, TemplateResponse)
    assert len(result.context_data['object_list']) == 1


@pytest.mark.asyncio()
@pytest.mark.django_db()
@pytest.mark.usefixtures('django_login', 'all_jobs')
async def test_deferred_queue_jobs_view(async_client: AsyncClient) -> None:
    url = reverse('arq_admin:deferred_jobs', kwargs={'queue_name': default_queue_name})

    result = await async_client.get(url)
    assert isinstance(result, TemplateResponse)
    assert len(result.context_data['object_list']) == 1


@pytest.mark.asyncio()
@pytest.mark.django_db()
@pytest.mark.usefixtures('django_login', 'all_jobs')
async def test_job_detail_view(redis: ArqRedis, async_client: AsyncClient) -> None:
    keys = await redis.keys(job_key_prefix + '*')
    job_id = keys[0][len(job_key_prefix):].decode('utf-8')

    url = reverse('arq_admin:job_detail', kwargs={'queue_name': default_queue_name, 'job_id': job_id})

    result = await async_client.get(url)
    assert isinstance(result, TemplateResponse)
    assert result.context_data['object'].job_id == job_id


@pytest.mark.asyncio()
@pytest.mark.django_db()
@pytest.mark.usefixtures('django_login', 'all_jobs')
async def test_get_job_abort_view(redis: ArqRedis, async_client: AsyncClient) -> None:
    keys = await redis.keys(job_key_prefix + '*')
    job_id = keys[0][len(job_key_prefix):].decode('utf-8')

    url = reverse('arq_admin:job_abort', kwargs={'queue_name': default_queue_name, 'job_id': job_id})

    result = await async_client.get(url)
    assert isinstance(result, TemplateResponse)
    assert result.context_data['object'].job_id == job_id


@pytest.mark.asyncio()
@pytest.mark.django_db()
@patch.object(Queue, 'abort_job')
@pytest.mark.usefixtures('django_login', 'all_jobs')
@pytest.mark.parametrize(
    ('abort_return_value', 'message_tag'),
    [
        (True, 'success'),
        (False, 'error'),
        (None, 'warning'),
    ],
)
async def test_post_job_abort_view(
    mocked_abort_job: AsyncMock,
    redis: ArqRedis,
    async_client: AsyncClient,
    abort_return_value: bool,
    message_tag: str,
) -> None:
    mocked_abort_job.return_value = abort_return_value
    keys = await redis.keys(job_key_prefix + '*')
    job_id = keys[0][len(job_key_prefix):].decode('utf-8')

    url = reverse('arq_admin:job_abort', kwargs={'queue_name': default_queue_name, 'job_id': job_id})

    response = await async_client.post(url)
    assert isinstance(response, HttpResponseRedirect)
    messages = list(get_messages(response.asgi_request))
    assert len(messages) == 1
    message = messages[0]
    assert message.tags == message_tag
