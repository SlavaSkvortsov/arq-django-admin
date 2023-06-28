import warnings
from collections import defaultdict
from typing import Any, Dict

from arq.connections import RedisSettings
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

if not hasattr(settings, 'ARQ_QUEUES'):
    raise ImproperlyConfigured('You have to define ARQ_QUEUES in settings.py')

ARQ_QUEUES: Dict[str, RedisSettings] = settings.ARQ_QUEUES

if not all(isinstance(redis_settings, RedisSettings) for redis_settings in ARQ_QUEUES.values()):
    raise ImproperlyConfigured('All values of "ARQ_QUEUES" must be RedisSettings')

ARQ_DESERIALIZER = getattr(settings, 'ARQ_DESERIALIZER', None)
ARQ_DESERIALIZER_BY_QUEUE = getattr(settings, 'ARQ_DESERIALIZER_BY_QUEUE', {})

if ARQ_DESERIALIZER:
    warnings.warn('ARQ_DESERIALIZER is deprecated, use ARQ_DESERIALIZER_BY_QUEUE', DeprecationWarning)

    if ARQ_DESERIALIZER_BY_QUEUE:
        raise ImproperlyConfigured('You cannot define both ARQ_DESERIALIZER and ARQ_DESERIALIZER_BY_QUEUE')

    ARQ_DESERIALIZER_BY_QUEUE = defaultdict(lambda: ARQ_DESERIALIZER)

ARQ_JOB_ABORT_TIMEOUT = getattr(settings, 'ARQ_JOB_ABORT_TIMEOUT', 5)

ARQ_MAX_CONNECTIONS = getattr(settings, 'ARQ_MAX_CONNECTIONS', 100)
