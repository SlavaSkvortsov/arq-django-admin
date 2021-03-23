from contextlib import asynccontextmanager
from typing import AsyncGenerator

from arq.connections import ArqRedis, RedisSettings, create_pool


@asynccontextmanager
async def get_redis(setting: RedisSettings) -> AsyncGenerator[ArqRedis, None]:
    redis = await create_pool(setting)
    try:
        yield redis
    finally:
        redis.close()
        await redis.wait_closed()
