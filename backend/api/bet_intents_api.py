# -*- coding: utf-8 -*-
"""Bet Intent API (Hash-Coupon)."""
import json
import random
import string
from pathlib import Path
from datetime import datetime, timezone, timedelta
from aiohttp import web

from backend.db.supabase_client import db


OUTCOME_MAP = {
    "П1": "p1",
    "X": "x",
    "П2": "p2",
    "1X": "p1x",
    "12": "p12",
    "X2": "px2",
}


def _load_matches_cache() -> dict:
    p = Path(__file__).resolve().parents[2] / "frontend" / "matches.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {str(m.get("id")): m for m in data.get("matches", []) if m.get("id")}


def _extract_odds(match: dict, outcome: str):
    key = OUTCOME_MAP.get(outcome)
    if not key:
        return None
    val = match.get(key)
    if not val or val in ("—", "-", "0", "0.00"):
        return None
    try:
        return round(float(val), 2)
    except Exception:
        return None


def _intent_hash(length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


async def create_intent(request: web.Request):
    if not db.initialized:
        db.init()
    if not db.initialized:
        return web.json_response({"error": "Database not configured"}, status=500)

    payload = await request.json()
    match_id = str(payload.get("match_id", "")).strip()
    outcome = str(payload.get("outcome", "")).strip().upper()
    sender_wallet = str(payload.get("sender_wallet", "")).strip().upper()

    if not match_id or not outcome or not sender_wallet:
        return web.json_response({"error": "match_id, outcome, sender_wallet are required"}, status=400)

    matches = _load_matches_cache()
    match = matches.get(match_id)
    if not match:
        return web.json_response({"error": "match not found in current cache"}, status=404)

    odds = _extract_odds(match, outcome)
    if not odds:
        return web.json_response({"error": "outcome/odds unavailable"}, status=400)

    intent = None
    for _ in range(10):
        h = _intent_hash(6)
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        try:
            await db.create_bet_intent(
                intent_hash=h,
                match_id=match_id,
                sender_wallet=sender_wallet,
                outcome=outcome,
                odds_fixed=odds,
                expires_at=expires_at,
            )
            intent = {"intent_hash": h, "odds_fixed": odds, "expires_at": expires_at}
            break
        except Exception:
            continue

    if not intent:
        return web.json_response({"error": "failed to create intent"}, status=500)

    return web.json_response(intent)


async def health(_: web.Request):
    return web.json_response({"ok": True})


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_post("/api/intents", create_intent)
    return app


if __name__ == "__main__":
    db.init()
    web.run_app(create_app(), host="0.0.0.0", port=8081)
