from core.logger import logger
from db.database import redis_client, redis
from typing import Dict
import json


class CacheManager:
    def __init__(self, manager: redis.Redis = redis_client):
        self.manager = manager

    async def set(self, key: str, content: Dict, func: str, ttl: int = 300):
        try:
            payload = json.dumps(content, default=str)
            await self.manager.setex(key, ttl, payload)
            logger.info(f"[{func}] Cache SET - Key {key}")
        except (TypeError, ValueError) as e:
            logger.error(f"[{func}] Cache SERIALIZATION FAIL - Key: {key} | Error: {e}")
        except redis.RedisError as e:
            logger.error(f"[{func}] Cache FAIL - Key: {key} | Error: {e}")

    async def get(self, key: str, func: str):
        try:
            result = await self.manager.get(key)
            if result is not None:
                logger.info(f"[{func}] Cache HIT - Key: {key}")
                return json.loads(result)
            logger.info(f"[{func}] Cache MISS - Key: {key}")
            return
        except (TypeError, ValueError) as e:
            logger.error(f"[{func}] Cache SERIALIZATION FAIL - Key: {key} | Error: {e}")
        except redis.RedisError as e:
            logger.error(f"[{func}] Cache FAIL - Key: {key} | Error: {e}")

    async def delete(self, key: str, func: str):
        try:
            await self.manager.delete(key)
            logger.info(f"[{func}] Cache DELETE - Key: {key}")
            return
        except redis.RedisError as e:
            logger.error(f"[{func}] Cache DELETE FAIL - Key: {key} | Error: {e}")

cache_manager = CacheManager()