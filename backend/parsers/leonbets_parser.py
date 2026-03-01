#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Leonbets JSON API Parser
Based on: https://github.com/Vlad110200/Leon-parser
"""

import json
from datetime import datetime
from typing import List, Dict, Optional
from backend.parsers.base_parser import BaseParser

BASE_URL = "https://leon.ru"

SPORTS_MAP = {
    "Football": "football",
    "Basketball": "basket",
    "Ice Hockey": "hockey",
    "Tennis": "tennis",
}

class LeonbetsParser(BaseParser):
    """Leonbets JSON API Parser"""
    
    def __init__(self):
        super().__init__("Leonbets", BASE_URL)
    
    async def parse(self) -> List[Dict]:
        """Parse matches from Leonbets"""
        await self.init_session()
        url = f"{BASE_URL}/api-2/betline/events/all"
        params = {
            "ctag": "ru-RU",
            "flags": "all",
        }
        
        headers = {
            "Accept": "application/json",
            "Referer": "https://leon.ru/",
        }
        
        try:
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    print(f"[ERROR] Leonbets returned {response.status}")
                    return []
                
                data = await response.json()
                matches = []
                
                sports = data.get("sports", [])
                
                for sport in sports:
                    sport_name = sport.get("name", "")
                    sport_key = SPORTS_MAP.get(sport_name)
                    
                    if not sport_key:
                        continue
                    
                    for region in sport.get("regions", []):
                        league_name = region.get("name", "")
                        
                        for competition in region.get("competitions", []):
                            for event in competition.get("events", []):
                                match = self.parse_event(event, sport_key, league_name)
                                if match:
                                    matches.append(match)
                
                return matches
        
        except Exception as e:
            print(f"[ERROR] Leonbets: {e}")
            return []
    
    def parse_event(self, event: Dict, sport_key: str, league_name: str) -> Optional[Dict]:
        """Parse single event"""
        event_id = event.get("id")
        event_name = event.get("name", "")
        
        # Extract teams
        teams = event_name.split(" - ")
        if len(teams) != 2:
            return None
        
        home_team, away_team = teams[0].strip(), teams[1].strip()
        
        # Parse kickoff time
        kickoff = event.get("kickoff", 0)
        match_time = None
        if kickoff:
            dt = datetime.fromtimestamp(kickoff / 1000)
            match_time = dt.isoformat()
        
        match_data = {
            "external_id": f"leon_{event_id}",
            "sport": sport_key,
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
        
        # Parse markets
        for market in event.get("markets", []):
            market_name = market.get("name", "")
            runners = market.get("runners", [])
            
            if market_name == "1X2":
                for runner in runners:
                    runner_name = runner.get("name", "")
                    price = runner.get("price", {}).get("num", 0)
                    
                    if runner_name == "1":
                        match_data["odds_1"] = float(price)
                    elif runner_name == "X":
                        match_data["odds_x"] = float(price)
                    elif runner_name == "2":
                        match_data["odds_2"] = float(price)
            
            elif "Total" in market_name:
                for runner in runners:
                    runner_name = runner.get("name", "")
                    price = runner.get("price", {}).get("num", 0)
                    param = runner.get("param")
                    
                    if "Over" in runner_name and param:
                        match_data["total_value"] = float(param)
                        match_data["total_over"] = float(price)
                    elif "Under" in runner_name:
                        match_data["total_under"] = float(price)
            
            elif "Handicap" in market_name:
                for runner in runners:
                    runner_name = runner.get("name", "")
                    price = runner.get("price", {}).get("num", 0)
                    param = runner.get("param")
                    
                    if param:
                        if "1" in runner_name or home_team in runner_name:
                            match_data["handicap_1_value"] = float(param)
                            match_data["handicap_1"] = float(price)
                        elif "2" in runner_name or away_team in runner_name:
                            match_data["handicap_2_value"] = float(param)
                            match_data["handicap_2"] = float(price)
        
        # No draw for tennis/basketball
        if sport_key in ["tennis", "basket"]:
            match_data["odds_x"] = 0.0
        
        return match_data
