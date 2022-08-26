import pytest
from arq import ArqRedis
from arq.constants import default_queue_name, job_key_prefix
from django.template.response import TemplateResponse
from django.test import AsyncClient
from django.urls import reverse


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
