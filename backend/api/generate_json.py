# -*- coding: utf-8 -*-
"""Generate matches.json from Database"""
import json
import asyncio
from backend.db.supabase_client import db

async def generate():
    """Generate matches.json"""
    db.init()
    matches = await db.get_matches(limit=500)
    
    with open("frontend/matches.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)
    
    print(f"Generated matches.json with {len(matches)} matches")

if __name__ == "__main__":
    asyncio.run(generate())
