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

    async def _fetch_fixtures(self, league_id: int) -> List[dict]:
        """Fetch upcoming fixtures for a league over the next DAYS_AHEAD days."""
        today = datetime.now(tz=timezone.utc)
        end = today + timedelta(days=DAYS_AHEAD)
        # European leagues run Aug–May: in Jan–Jul the current season started the prior year
        season = today.year if today.month >= 8 else today.year - 1
        params = {
            "league": league_id,
            "season": season,
            "from": today.strftime("%Y-%m-%d"),
            "to": end.strftime("%Y-%m-%d"),
            "status": "NS",  # Not Started
        }
        data = await self._get("/fixtures", params)
        return (data or {}).get("response", [])

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

        all_matches: List[Dict] = []

        for league_id, (sport_type, league_name) in LEAGUES.items():
            fixtures = await self._fetch_fixtures(league_id)
            for fixture in fixtures:
                f = fixture.get("fixture", {})
                teams = fixture.get("teams", {})
                fixture_id = f.get("id")
                if not fixture_id:
                    continue

                home = teams.get("home", {}).get("name", "")
                away = teams.get("away", {}).get("name", "")
                date_str = f.get("date", "")

                try:
                    match_time = datetime.fromisoformat(
                        date_str.replace("Z", "+00:00")
                    ).isoformat()
                except Exception:
                    match_time = date_str

                match_data = {
                    "external_id": f"apifootball_{fixture_id}",
                    "sport": sport_type,
                    "league": league_name,
                    "home_team": home,
                    "away_team": away,
                    "match_time": match_time,
                    "match_url": f"https://www.api-football.com/fixture/{fixture_id}",
                    "odds_1": 0.0,
                    "odds_x": 0.0,
                    "odds_2": 0.0,
                    "total_value": None,
                    "total_over": 0.0,
                    "total_under": 0.0,
                    "handicap_1_value": None,
                    "handicap_1": 0.0,
                    "handicap_2_value": None,
                    "handicap_2": 0.0,
                    "is_live": False,
                }

                odds_resp = await self._fetch_odds(fixture_id)
                if odds_resp:
                    self._parse_odds(odds_resp, match_data)

                if match_data["odds_1"] > 0 or match_data["odds_2"] > 0:
                    all_matches.append(match_data)

            added = sum(1 for m in all_matches if m.get("league") == league_name)
            print(f"[ApiFootball] {league_name}: {len(fixtures)} fetched, {added} with odds")

        return all_matches
