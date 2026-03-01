#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The Odds API v4 Parser with Totals and Spreads support
Official API: https://the-odds-api.com/liveapi/guides/v4/
"""

import os
import aiohttp
import json
from datetime import datetime
from typing import List, Dict, Optional
from backend.parsers.base_parser import BaseParser

API_KEY = os.getenv("ODDS_API_KEY", "")
BASE_URL = "https://api.the-odds-api.com/v4"

SPORTS_MAP = {
    "soccer_uefa_champions_league": ("football", "Лига чемпионов УЕФА"),
    "soccer_epl": ("football", "Англия. Премьер-лига"),
    "soccer_spain_la_liga": ("football", "Испания. Ла Лига"),
    "basketball_nba": ("basket", "NBA"),
    "icehockey_nhl": ("hockey", "НХЛ"),
}

class OddsAPIParser(BaseParser):
    """The Odds API v4 Parser"""
    
    def __init__(self):
        super().__init__("OddsAPI", BASE_URL)
    
    async def parse(self) -> List[Dict]:
        """Parse matches from The Odds API"""
        all_matches = []
        
        for sport_key, (sport_type, league_name) in SPORTS_MAP.items():
            matches = await self.fetch_sport_odds(sport_key, sport_type, league_name)
            all_matches.extend(matches)
        
        return all_matches
    
    async def fetch_sport_odds(self, sport_key: str, sport_type: str, league_name: str) -> List[Dict]:
        """Fetch odds for specific sport"""
        await self.init_session()
        url = f"{BASE_URL}/sports/{sport_key}/odds"
        params = {
            "apiKey": API_KEY,
            "regions": "eu,us",
            "markets": "h2h,totals,spreads",
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    print(f"[ERROR] The Odds API returned {response.status}")
                    return []
                
                # Check API quota
                remaining = response.headers.get("x-requests-remaining", "?")
                print(f"  [QUOTA] {sport_key}: Remaining {remaining}")
                
                data = await response.json()
                matches = []
                
                for event in data:
                    match = self.parse_event(event, sport_type, league_name)
                    if match:
                        matches.append(match)
                
                return matches
        
        except Exception as e:
            print(f"[ERROR] {sport_key}: {e}")
            return []
    
    def parse_event(self, event: Dict, sport_type: str, league_name: str) -> Optional[Dict]:
        """Parse single event"""
        event_id = event.get("id", "")
        home_team = event.get("home_team", "")
        away_team = event.get("away_team", "")
        
        # Parse commence time
        commence_time = event.get("commence_time", "")
        match_time = None
        if commence_time:
            try:
                dt = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
                match_time = dt.isoformat()
            except Exception:
                pass
        
        # Initialize match data
        match_data = {
            "external_id": f"odds_{event_id}",
            "sport": sport_type,
            "league": league_name,
            "home_team": home_team,
            "away_team": away_team,
            "match_time": match_time,
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
        }
        
        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            return None
        
        # Use first bookmaker
        first_bookie = bookmakers[0]
        markets = first_bookie.get("markets", [])
        
        for market in markets:
            market_key = market.get("key", "")
            outcomes = market.get("outcomes", [])
            
            if market_key == "h2h":
                self.parse_h2h(outcomes, home_team, away_team, match_data, sport_type)
            elif market_key == "totals":
                self.parse_totals(outcomes, match_data)
            elif market_key == "spreads":
                self.parse_spreads(outcomes, home_team, away_team, match_data)
        
        return match_data
    
    def parse_h2h(self, outcomes: List[Dict], home_team: str, away_team: str, 
                  match_data: Dict, sport_type: str):
        """Parse h2h market"""
        for outcome in outcomes:
            name = outcome.get("name", "")
            price = outcome.get("price", 0)
            
            if name == home_team:
                match_data["odds_1"] = float(price)
            elif name == away_team:
                match_data["odds_2"] = float(price)
            elif name == "Draw":
                match_data["odds_x"] = float(price)
        
        # No draw for tennis/basketball
        if sport_type in ["tennis", "basket"]:
            match_data["odds_x"] = 0.0
    
    def parse_totals(self, outcomes: List[Dict], match_data: Dict):
        """Parse totals market"""
        total_point = None
        
        for outcome in outcomes:
            name = outcome.get("name", "")
            price = outcome.get("price", 0)
            point = outcome.get("point", 0)
            
            if name == "Over":
                match_data["total_over"] = float(price)
                total_point = point
            elif name == "Under":
                match_data["total_under"] = float(price)
                total_point = point
        
        if total_point:
            match_data["total_value"] = float(total_point)
    
    def parse_spreads(self, outcomes: List[Dict], home_team: str, away_team: str, match_data: Dict):
        """Parse spreads market"""
        for outcome in outcomes:
            name = outcome.get("name", "")
            price = outcome.get("price", 0)
            point = outcome.get("point", 0)
            
            if name == home_team:
                match_data["handicap_1_value"] = float(point)
                match_data["handicap_1"] = float(price)
            elif name == away_team:
                match_data["handicap_2_value"] = float(point)
                match_data["handicap_2"] = float(price)
