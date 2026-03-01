import os
import sys
import json
import time
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Add backend to path to import config if needed
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from backend.bot.telegram_bot import load_bets, save_bets, fmt_bet, BOT_TOKEN
from telegram.ext import Application

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# Very simple auto-settler mock for testing ApiFootball matches
async def check_match_results(bot=None):
    log.info("Checking for finished matches to settle bets...")
    bets = load_bets()
    updated = False

    # Find pending bets
    for bet in bets:
        if bet.get("status") == "pending":
            log.info(f"Checking pending bet: {bet.get('id')} for match {bet.get('match_id')}")
            
            # --- MOCK RESULT RESOLVER FOR PROOF OF CONCEPT ---
            # In production, we would query ApiFootball for the final match result using bet['match_id']
            # For now, if the bet is older than 2 hours (or for demonstration), let's simulate a win
            # Let's just simulate a 50/50 win/loss for the demo if a test flag is set, 
            # or skip if it's a real bet waiting for real API integration.
            
            # TODO: Real API Football integration will go here:
            # result = await fetch_apifootball_result(bet['match_id'])
            # if result['status'] == 'Match Finished':
            #     is_win = calculate_win(bet['bet_type'], result['score_home'], result['score_away'])
            
            pass

    if updated:
        save_bets(bets)

async def main():
    log.info("Starting Auto-Settler Service...")
    app = Application.builder().token(BOT_TOKEN).build()
    
    while True:
        try:
            await check_match_results(app.bot)
        except Exception as e:
            log.error(f"Error in auto settler: {e}")
        
        await asyncio.sleep(60 * 15)  # Check every 15 minutes

if __name__ == "__main__":
    asyncio.run(main())
