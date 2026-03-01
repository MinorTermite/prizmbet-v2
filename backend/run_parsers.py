#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PrizmBet v2 - Parser Orchestrator
Runs all parsers in parallel and aggregates results
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.parsers.api_football_parser import APIFootballParser
from backend.parsers.fonbet_api_parser import FonbetAPIParser
from backend.parsers.fallback_generator import FallbackGenerator
from backend.db.supabase_client import db
from backend.utils.redis_client import cache
from backend.utils.telegram import telegram

def main():
    """Run all parsers"""
    print("=" * 60)
    print("PrizmBet v2 - Starting parsers...")
    print("=" * 60)
    
    # Initialize connections
    db.init()
    await cache.connect()
    
    # Initialize parsers
    parsers = [
        APIFootballParser(),      # Primary: API-Football (100 req/day)
        FonbetAPIParser(),         # Secondary: Fonbet public API
        FallbackGenerator()        # Fallback: Generated matches if APIs fail
    ]
    
    # Run parsers in parallel
    results = await asyncio.gather(*[p.run() for p in parsers], return_exceptions=True)
    
    # Calculate totals
    total_matches = 0
    successful = 0
    failed = 0
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"❌ {parsers[i].name} failed: {result}")
            failed += 1
        else:
            total_matches += result
            successful += 1
            print(f"✅ {parsers[i].name}: {result} matches")
    
    # Close connections
    await cache.close()
    
    print("=" * 60)
    print(f"SUMMARY: {total_matches} matches from {successful}/{len(parsers)} parsers")
    print("=" * 60)
    
    # Send Telegram notification
    if total_matches > 0:
        await telegram.send_message(
            f"✅ <b>Parsers completed</b>\n\n"
            f"Total matches: {total_matches}\n"
            f"Successful: {successful}/{len(parsers)}\n"
            f"Failed: {failed}"
        )
    
    return total_matches

if __name__ == "__main__":
    try:
        total = asyncio.run(main())
        sys.exit(0 if total > 0 else 1)
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        asyncio.run(telegram.send_alert("Parser Fatal Error", str(e)))
        sys.exit(1)