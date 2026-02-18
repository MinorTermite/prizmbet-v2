# -*- coding: utf-8 -*-
"""Health Check Script"""
import asyncio
import aiohttp
from datetime import datetime
from backend.utils.telegram import telegram
from backend.utils.redis_client import cache
from backend.db.supabase_client import db

async def check_website(url: str, name: str):
    """Check if website is up"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                return response.status == 200
    except Exception:
        return False

async def check_database():
    """Check database connection"""
    if not db.initialized:
        return False
    try:
        matches = await db.get_matches(limit=1)
        return True
    except Exception:
        return False

async def check_cache():
    """Check cache connection"""
    if not cache.initialized:
        return False
    try:
        test_key = "health_check:test"
        await cache.set(test_key, "1", expire=10)
        value = await cache.get(test_key)
        await cache.delete(test_key)
        return value == "1"
    except Exception:
        return False

async def run_health_check():
    """Run all health checks"""
    print("Running Health Check...")
    
    results = {
        "github_pages": await check_website("https://minortermite.github.io/betprizm/", "GitHub Pages"),
        "database": await check_database(),
        "cache": await check_cache()
    }
    
    all_healthy = all(results.values())
    
    if all_healthy:
        print("All systems healthy")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"Failed: {', '.join(failed)}")
        await telegram.send_alert("Health Check Failed", f"Failed: {', '.join(failed)}")
    
    return all_healthy

if __name__ == "__main__":
    asyncio.run(run_health_check())
