from contextlib import asynccontextmanager
from typing import AsyncGenerator

from arq.connections import ArqRedis, RedisSettings, create_pool
from arq_admin.utils import is_redis_py


@asynccontextmanager
async def get_redis(setting: RedisSettings) -> AsyncGenerator[ArqRedis, None]:
    redis = await create_pool(setting)
    try:
        yield redis
    finally:
        # arq 0.23 or newer
        if is_redis_py(redis):
            await redis.close()  # type: ignore
        # arq 0.22 or before
        else:
            redis.close()  # type: ignore
            await redis.wait_closed()  # type: ignore
