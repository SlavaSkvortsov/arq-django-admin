from arq.connections import ArqRedis

def is_redis_py(redis: ArqRedis) -> bool:
    """Returns True if using redis-py instead of aioredis"""

    return not hasattr(redis, 'wait_closed')
