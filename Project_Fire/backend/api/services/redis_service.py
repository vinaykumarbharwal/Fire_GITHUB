import logging
import json
from typing import Any, Optional
import os

logger = logging.getLogger(__name__)

class RedisCache:
    """
    Dummy cache service that replaces Redis.
    The user requested removal of Redis to avoid connection errors.
    """
    def __init__(self):
        self.redis = None
        logger.info("📡 Redis cache disabled by user request. Running in no-cache mode.")

    def get(self, key: str) -> Optional[Any]:
        return None

    def set(self, key: str, value: Any, expire: int = 3600):
        return None

cache = RedisCache()
