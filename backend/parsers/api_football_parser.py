# -*- coding: utf-8 -*-
"""
API-Football Parser (api-football.com via RapidAPI)
Docs: https://www.api-football.com/documentation-v3
Provides: fixtures, live scores, odds (pre-match and live).
"""

import os
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from backend.parsers.base_parser import BaseParser

API_KEY = os.getenv("API_FOOTBALL_KEY", "")
BASE_URL = "https://v3.football.api-sports.io"

# League IDs → (sport_type, league_name)
LEAGUES: Dict[int, tuple] = {
    2:   ("football", "Лига чемпионов УЕФА"),
    3:   ("football", "Лига Европы УЕФА"),
    39:  ("football", "Англия. Премьер-лига"),
    140: ("football", "Испания. Ла Лига"),
    135: ("football", "Италия. Серия А"),
    78:  ("football", "Германия. Бундеслига"),
    61:  ("football", "Франция. Лига 1"),
    94:  ("football", "Португалия. Примейра"),
    203: ("football", "Турция. Суперлига"),
}

# Fetch fixtures N days into the future
DAYS_AHEAD = 3


class ApiFootballParser(BaseParser):
    """API-Football v3 Parser"""

    def __init__(self):
        super().__init__("ApiFootball", BASE_URL)

    def _headers(self) -> Dict[str, str]:
        return {
            "x-apisports-key": API_KEY,
            "x-rapidapi-host": "v3.football.api-sports.io",
        }

    async def _get(self, path: str, params: dict) -> Optional[dict]:
        """GET request to API-Football."""
        await self.init_session()
        url = f"{BASE_URL}{path}"
        try:
            async with self.session.get(url, headers=self._headers(), params=params, proxy=self.proxy) as r:
                if r.status != 200:
                    print(f"[ApiFootball] HTTP {r.status} for {path}")
                    return None
                return await r.json()
        except Exception as e:
            print(f"[ApiFootball] Request error {path}: {e}")
            return None

    async def _fetch_fixtures_by_date(self) -> List[dict]:
        """Fetch fixtures for the next DAYS_AHEAD days via date param (free-plan compatible).
        Filters results client-side to LEAGUES of interest.
        """
        today = datetime.now(tz=timezone.utc)
        all_fixtures: List[dict] = []
        league_ids = set(LEAGUES.keys())

        for offset in range(DAYS_AHEAD + 1):
            date_str = (today + timedelta(days=offset)).strftime("%Y-%m-%d")
            data = await self._get("/fixtures", {"date": date_str})
            for fix in (data or {}).get("response", []):
                if fix.get("league", {}).get("id") in league_ids:
                    all_fixtures.append(fix)

        # Also grab live fixtures
        live_data = await self._get("/fixtures", {"live": "all"})
        for fix in (live_data or {}).get("response", []):
            if fix.get("league", {}).get("id") in league_ids:
                all_fixtures.append(fix)

        return all_fixtures

    async def _fetch_odds(self, fixture_id: int) -> Optional[dict]:
        """Fetch pre-match odds for a fixture."""
        data = await self._get("/odds", {"fixture": fixture_id})
        responses = (data or {}).get("response", [])
        if not responses:
            return None
        return responses[0]

    def _parse_odds(self, odds_response: dict, match_data: dict):
        """Extract h2h / totals odds from the odds response."""
        bookmakers = (odds_response or {}).get("bookmakers", [])
        for bk in bookmakers:
            for bet in bk.get("bets", []):
                name = bet.get("name", "")
                values = bet.get("values", [])

                if name in ("Match Winner", "1X2"):
                    for v in values:
                        label = v.get("value", "")
                        odd = float(v.get("odd", 0) or 0)
                        if label in ("Home", "1"):
                            match_data["odds_1"] = odd
                        elif label in ("Draw", "X"):
                            match_data["odds_x"] = odd
                        elif label in ("Away", "2"):
                            match_data["odds_2"] = odd

                elif name in ("Goals Over/Under", "Over/Under"):
                    for v in values:
                        label = v.get("value", "")
                        odd = float(v.get("odd", 0) or 0)
                        if label.startswith("Over"):
                            # Expected format: "Over 2.5" — gracefully handle compact "Over2.5"
                            parts = label.split(" ", 1)
                            try:
                                raw = parts[1] if len(parts) > 1 else parts[0][4:]
                                if raw:
                                    match_data["total_value"] = float(raw)
                            except (IndexError, ValueError):
                                pass
                            match_data["total_over"] = odd
                        elif label.startswith("Under"):
                            match_data["total_under"] = odd

    async def parse(self) -> List[Dict]:
        if not API_KEY:
            print("[ApiFootball] API_FOOTBALL_KEY not configured — skipping")
            return []

        # Fetch all fixtures via date-based query (free-plan compatible)
        fixtures = await self._fetch_fixtures_by_date()
        print(f"[ApiFootball] fetched {len(fixtures)} fixtures for target leagues")

        all_matches: List[Dict] = []
        seen_ids: set = set()

        for fixture in fixtures:
            f          = fixture.get("fixture", {})
            teams      = fixture.get("teams", {})
            league_obj = fixture.get("league", {})
            fixture_id = f.get("id")
            if not fixture_id or fixture_id in seen_ids:
                continue
            seen_ids.add(fixture_id)

            league_id   = league_obj.get("id")
            sport_type, league_name = LEAGUES.get(league_id, ("football", league_obj.get("name", "")))
            home        = teams.get("home", {}).get("name", "")
            away        = teams.get("away", {}).get("name", "")
            date_str    = f.get("date", "")
            status_long = f.get("status", {}).get("long", "")
            is_live     = status_long in ("First Half", "Second Half", "Halftime",
                                          "Extra Time", "Break Time", "Penalty In Progress")

            try:
                match_time = datetime.fromisoformat(
                    date_str.replace("Z", "+00:00")
                ).isoformat()
            except Exception:
                match_time = date_str

            match_data = {
                "external_id":       f"apifootball_{fixture_id}",
                "sport":             sport_type,
                "league":            league_name,
                "home_team":         home,
                "away_team":         away,
                "match_time":        match_time,
                "match_url":         f"https://www.api-football.com/fixture/{fixture_id}",
                "is_live":           is_live,
                "odds_1":            0.0,
                "odds_x":            0.0,
                "odds_2":            0.0,
                "total_value":       None,
                "total_over":        0.0,
                "total_under":       0.0,
                "handicap_1_value":  None,
                "handicap_1":        0.0,
                "handicap_2_value":  None,
                "handicap_2":        0.0,
            }

            odds_resp = await self._fetch_odds(fixture_id)
            if odds_resp:
                self._parse_odds(odds_resp, match_data)

            all_matches.append(match_data)

        print(f"[ApiFootball] {len(all_matches)} matches processed")
        return all_matches
