# -*- coding: utf-8 -*-
"""Redis Cache Client (Upstash)"""
import aioredis
from backend.config import config

class Cache:
    """Redis cache client"""
    
    def __init__(self):
        self.redis = None
        self.initialized = False
    
    async def connect(self):
        """Connect to Redis"""
        if not self.initialized and config.UPSTASH_REDIS_URL:
            try:
                self.redis = aioredis.from_url(
                    config.UPSTASH_REDIS_URL,
                    password=config.UPSTASH_REDIS_TOKEN,
                    decode_responses=True
                )
                self.initialized = True
                print("Redis connected")
            except Exception as e:
                print(f"Redis connection failed: {e}")
                self.initialized = False
    
    async def get(self, key: str):
        """Get value from cache"""
        if not self.initialized:
            return None
        try:
            return await self.redis.get(key)
        except Exception:
            return None
    
    async def set(self, key: str, value, expire: int = 3600):
        """Set value in cache"""
        if not self.initialized:
            return False
        try:
            await self.redis.set(key, value, ex=expire)
            return True
        except Exception:
            return False
    
    async def delete(self, key: str):
        """Delete key from cache"""
        if not self.initialized:
            return False
        try:
            await self.redis.delete(key)
            return True
        except Exception:
            return False
    
    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()

cache = Cache()
