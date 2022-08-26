from contextlib import asynccontextmanager
from typing import AsyncGenerator

from arq.connections import ArqRedis, RedisSettings, create_pool
from arq.constants import default_queue_name


@asynccontextmanager
async def get_redis(setting: RedisSettings, queue_name: str = default_queue_name) -> AsyncGenerator[ArqRedis, None]:
    redis = await create_pool(setting, default_queue_name=queue_name)
    try:
        yield redis
    finally:
        await redis.close()
