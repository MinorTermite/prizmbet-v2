# -*- coding: utf-8 -*-
"""
Generate frontend/matches.json from live parser data.

Runs all parsers directly (no Supabase required) and writes the JSON file
in the legacy frontend format expected by index.html:
  { last_update, source, total, matches: [{team1, team2, p1, x, p2, ...}] }
"""
import sys
import json
import asyncio
import os
from datetime import datetime, timezone
from typing import List, Dict, Any

# Allow running as both `python backend/api/generate_json.py` and
# `python -m backend.api.generate_json` from the repo root.
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

MONTHS_RU = ["янв", "фев", "мар", "апр", "май", "июн",
             "июл", "авг", "сен", "окт", "ноя", "дек"]

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "matches.json")


def _fmt_odd(value) -> str:
    """Format an odds float to a display string."""
    try:
        v = float(value)
        return f"{v:.2f}" if v > 0 else "—"
    except (TypeError, ValueError):
        return "—"


def _bookmaker_from_id(external_id: str) -> str:
    eid = (external_id or "").lower()
    if eid.startswith("apifootball_"):
        return "ApiFootball"
    if eid.startswith("odds_"):
        return "OddsAPI"
    if eid.startswith("1xbet_live"):   # must come before the generic 1xbet_ check
        return "1xBet Live"
    if eid.startswith("1xbet_"):
        return "1xBet"
    if eid.startswith("leon_"):
        return "Leonbets"
    if eid.startswith("pinnacle_"):
        return "Pinnacle"
    return "unknown"


def to_frontend(match: Dict[str, Any]) -> Dict[str, Any]:
    """Convert parser match dict → legacy frontend dict."""
    date_str = time_str = ""
    raw_time = match.get("match_time", "")
    if raw_time:
        try:
            dt = datetime.fromisoformat(str(raw_time).replace("Z", "+00:00"))
            dt_msk = dt.astimezone(timezone.utc)  # display in UTC for consistency
            date_str = f"{dt_msk.day} {MONTHS_RU[dt_msk.month - 1]}"
            time_str = dt_msk.strftime("%H:%M")
        except Exception:
            pass

    return {
        "sport":     match.get("sport", ""),
        "league":    match.get("league", ""),
        "id":        match.get("external_id", ""),
        "date":      date_str,
        "time":      time_str,
        "team1":     match.get("home_team", ""),
        "team2":     match.get("away_team", ""),
        "match_url": match.get("match_url", ""),
        "p1":        _fmt_odd(match.get("odds_1")),
        "x":         _fmt_odd(match.get("odds_x")),
        "p2":        _fmt_odd(match.get("odds_2")),
        "p1x":       "—",
        "p12":       "—",
        "px2":       "—",
        "source":    _bookmaker_from_id(match.get("external_id", "")),
        # Extra fields kept for potential future use
        "total_value":      match.get("total_value"),
        "total_over":       _fmt_odd(match.get("total_over")),
        "total_under":      _fmt_odd(match.get("total_under")),
        "handicap_1_value": match.get("handicap_1_value"),
        "handicap_1":       _fmt_odd(match.get("handicap_1")),
        "handicap_2_value": match.get("handicap_2_value"),
        "handicap_2":       _fmt_odd(match.get("handicap_2")),
        "is_live":          bool(match.get("is_live", False)),
    }


def _write_json(matches: List[Dict[str, Any]]) -> int:
    """Serialize converted matches to frontend/matches.json and return count."""
    payload = {
        "last_update": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "source": "multi-parser",
        "total": len(matches),
        "matches": matches,
    }

    out = os.path.normpath(OUT_PATH)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[generate_json] Wrote {len(matches)} matches → {out}")
    return len(matches)


async def collect_all_matches() -> List[Dict[str, Any]]:
    """Run all parsers concurrently and return combined match list."""
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

    results = await asyncio.gather(
        *[p.parse() for p in parsers],
        return_exceptions=True,
    )

    all_matches: List[Dict[str, Any]] = []
    names = ["OddsAPI", "1xBet", "Leonbets", "Pinnacle", "ApiFootball"]
    for name, result in zip(names, results):
        if isinstance(result, Exception):
            print(f"[generate_json] {name} error: {result}")
        elif isinstance(result, list):
            print(f"[generate_json] {name}: {len(result)} matches")
            all_matches.extend(result)

    # Close all sessions
    for p in parsers:
        await p.close_session()

    return all_matches


async def generate_from_raw(raw: List[Dict[str, Any]]) -> int:
    """Convert pre-collected parser matches and write frontend/matches.json.

    Use this when the caller has already run the parsers (e.g. run_parsers.py)
    to avoid running the full parser network a second time.
    """
    matches = [to_frontend(m) for m in raw]
    return _write_json(matches)


async def generate() -> int:
    """Run parsers, convert, write frontend/matches.json."""
    print("[generate_json] Starting parser run…")
    raw = await collect_all_matches()
    matches = [to_frontend(m) for m in raw]
    return _write_json(matches)


if __name__ == "__main__":
    asyncio.run(generate())
