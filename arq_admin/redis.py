from contextlib import asynccontextmanager
from email.policy import default
from typing import AsyncGenerator

from arq.constants import default_queue_name
from arq.connections import ArqRedis, RedisSettings, create_pool
from arq_admin.utils import is_redis_py


@asynccontextmanager
async def get_redis(setting: RedisSettings, queue_name: str = default_queue_name) -> AsyncGenerator[ArqRedis, None]:
    redis = await create_pool(setting, default_queue_name=queue_name)
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
