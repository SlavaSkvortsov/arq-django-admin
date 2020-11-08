from arq.connections import RedisSettings
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

ARQ_QUEUES = getattr(settings, 'ARQ_QUEUES', None)
if ARQ_QUEUES is None:
    raise ImproperlyConfigured('You have to define ARQ_QUEUES in settings.py')

if not all(isinstance(redis_settings, RedisSettings) for redis_settings in ARQ_QUEUES.values()):
    raise ImproperlyConfigured('All values of "ARQ_QUEUES" must be RedisSettings')

ARQ_DESERIALIZER = getattr(settings, 'ARQ_DESERIALIZER', None)
