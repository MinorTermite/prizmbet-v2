# -*- coding: utf-8 -*-
"""Main Parser Runner"""
import asyncio
from backend.db.supabase_client import db
from backend.utils.redis_client import cache

async def run_all_parsers():
    """Run all parsers"""
    print("=" * 50)
    print("PrizmBet v2 - Parser Runner")
    print("=" * 50)
    
    db.init()
    await cache.connect()
    
    # Import and run parsers here
    # from backend.parsers.marathon_parser import MarathonParser
    # parser = MarathonParser()
    # await parser.run()
    
    print("Parsers completed")
    await cache.close()

if __name__ == "__main__":
    asyncio.run(run_all_parsers())
