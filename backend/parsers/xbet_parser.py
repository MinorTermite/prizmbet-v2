#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1xBet JSON API Parser with gzip decompression support
Based on: https://github.com/RRakibur06/sportsdata-parser
"""

import gzip
import json
from datetime import datetime
from typing import List, Dict, Optional
from backend.parsers.base_parser import BaseParser

BASE_URL = "https://1xbet.com"

SPORTS_MAP = {
    1: "football",
    2: "hockey",
    3: "basket",
    5: "tennis",
}

class XBetParser(BaseParser):
    """1xBet JSON API Parser"""
    
    def __init__(self):
        super().__init__("1xBet", BASE_URL)
    
    async def parse(self) -> List[Dict]:
        """Parse matches from 1xBet"""
        all_matches = []
        
        for sport_id, sport_name in SPORTS_MAP.items():
            matches = await self.fetch_sport_odds(sport_id, sport_name)
            all_matches.extend(matches)
        
        return all_matches
    
    async def fetch_sport_odds(self, sport_id: int, sport_name: str) -> List[Dict]:
        """Fetch odds for specific sport"""
        await self.init_session()
        url = f"{BASE_URL}/LineFeed/Get1x2_VZip"
        params = {
            "sports": sport_id,
            "count": 100,
            "lng": "ru",
            "mode": 4,
            "partner": 51,
            "getEmpty": "false",
        }
        
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate",
            "Referer": "https://1xbet.com/",
        }
        
        try:
            async with self.session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    print(f"[ERROR] 1xBet returned {response.status}")
                    return []
                
                content = await response.read()
                
                # Decompress gzip if needed
                if content[:2] == b'\x1f\x8b':
                    content = gzip.decompress(content)
                
                data = json.loads(content.decode('utf-8'))
                
                if not data.get("Success", False):
                    print(f"[WARN] 1xBet API returned Success=false")
                    return []
                
                events = data.get("Value", [])
                matches = []
                
                for event in events:
                    match = self.parse_event(event, sport_name)
                    if match:
                        matches.append(match)
                
                return matches
        
        except Exception as e:
            print(f"[ERROR] 1xBet {sport_name}: {e}")
            return []
    
    def parse_event(self, event: Dict, sport_name: str) -> Optional[Dict]:
        """Parse single event"""
        event_id = event.get("FI") or event.get("I")
        if not event_id:
            return None
        
        league = event.get("L", "")
        home_team = event.get("O1", "")
        away_team = event.get("O2", "")
        
        # Parse start time
        start_time = event.get("S", 0) or event.get("T", 0)
        match_time = None
        if start_time:
            dt = datetime.fromtimestamp(start_time)
            match_time = dt.isoformat()
        
        match_data = {
            "external_id": f"1xbet_{event_id}",
            "sport": sport_name,
            "league": league,
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
        
        selections = event.get("SE", []) or event.get("E", [])
        
        for sel in selections:
            sel_type = sel.get("S")
            coef = sel.get("C", 0)
            param = sel.get("P")
            
            # Main outcomes (1X2)
            if sel_type == 1:
                match_data["odds_1"] = float(coef)
            elif sel_type == 2:
                match_data["odds_x"] = float(coef)
            elif sel_type == 3:
                match_data["odds_2"] = float(coef)
            
            # Totals
            elif sel_type == 5 and param:
                match_data["total_value"] = float(param)
                match_data["total_over"] = float(coef)
            elif sel_type == 6 and param:
                match_data["total_under"] = float(coef)
            
            # Handicaps
            elif sel_type == 7 and param:
                match_data["handicap_1_value"] = float(param)
                match_data["handicap_1"] = float(coef)
            elif sel_type == 8 and param:
                match_data["handicap_2_value"] = float(param)
                match_data["handicap_2"] = float(coef)
        
        # No draw for tennis/basketball
        if sport_name in ["tennis", "basket"]:
            match_data["odds_x"] = 0.0
        
        return match_data
