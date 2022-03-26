from typing import Dict

from arq.connections import RedisSettings
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

if not hasattr(settings, 'ARQ_QUEUES'):
    raise ImproperlyConfigured('You have to define ARQ_QUEUES in settings.py')

ARQ_QUEUES: Dict[str, RedisSettings] = settings.ARQ_QUEUES

if not all(isinstance(redis_settings, RedisSettings) for redis_settings in ARQ_QUEUES.values()):
    raise ImproperlyConfigured('All values of "ARQ_QUEUES" must be RedisSettings')

ARQ_DESERIALIZER = getattr(settings, 'ARQ_DESERIALIZER', None)
