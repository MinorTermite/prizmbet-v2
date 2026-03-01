# -*- coding: utf-8 -*-
"""Main Parser Runner"""
import asyncio
from backend.db.supabase_client import db
from backend.utils.redis_client import cache

async def run_all_parsers():
    """Run all parsers, save to Supabase/cache, and write frontend/matches.json."""
    print("=" * 50)
    print("PrizmBet v2 - Parser Runner")
    print("=" * 50)

    db.init()
    await cache.connect()

    from backend.parsers.odds_api_parser import OddsAPIParser
    from backend.parsers.xbet_parser import XBetParser
    from backend.parsers.leonbets_parser import LeonbetsParser
    from backend.parsers.pinnacle_parser import PinnacleParser
    from backend.parsers.api_football_parser import ApiFootballParser

    parsers = [
        OddsAPIParser(),
        XBetParser(),
        LeonbetsParser(),
        PinnacleParser(),
        ApiFootballParser(),
    ]

    tasks = [parser.run() for parser in parsers]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    total_matches = sum(r for r in results if isinstance(r, int))
    print(f"\nTotal matches parsed: {total_matches}")

    # Also regenerate frontend/matches.json so GitHub Pages stays up-to-date
    if total_matches > 0:
        try:
            from backend.api.generate_json import generate
            await generate()
        except Exception as e:
            print(f"[run_parsers] generate_json failed: {type(e).__name__}: {e}")

    await cache.close()

if __name__ == "__main__":
    asyncio.run(run_all_parsers())

