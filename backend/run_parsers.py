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
    
    from backend.parsers.odds_api_parser import OddsAPIParser
    from backend.parsers.xbet_parser import XBetParser
    from backend.parsers.leonbets_parser import LeonbetsParser
    from backend.parsers.pinnacle_parser import PinnacleParser

    parsers = [
        OddsAPIParser(),
        XBetParser(),
        LeonbetsParser(),
        PinnacleParser(),
    ]

    tasks = [parser.run() for parser in parsers]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    total_matches = sum(r for r in results if isinstance(r, int))
    print(f"\nTotal matches parsed: {total_matches}")

    await cache.close()

if __name__ == "__main__":
    asyncio.run(run_all_parsers())
