# -*- coding: utf-8 -*-
"""Base Parser Class"""
import asyncio
import aiohttp
from datetime import datetime
from backend.utils.rate_limiter import rate_limiter, ua_rotator
from backend.utils.telegram import telegram
from backend.db.supabase_client import db
from backend.utils.redis_client import cache
from backend.utils.team_mapping import team_normalizer

class BaseParser:
    """Base class for all parsers"""
    
    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url
        self.session = None
        self.matches = []
        self.proxy = None  # will be set from proxy_manager or config
    
    async def init_session(self):
        """Initialize HTTP session with optional proxy support."""
        if self.session is None:
            from backend.utils.proxy_manager import proxy_manager
            from backend.config import config
            proxy_url = None
            if config.PROXY_ENABLED and config.PROXY_URL:
                proxy_url = config.PROXY_URL
            elif config.PROXY_ENABLED:
                await proxy_manager.refresh_if_needed()
                proxy_url = proxy_manager.get_proxy()

            self.proxy = proxy_url

            connector = None
            if proxy_url and proxy_url.startswith('socks'):
                try:
                    from aiohttp_socks import ProxyConnector
                    connector = ProxyConnector.from_url(proxy_url)
                    self.proxy = None  # SOCKS handled by connector, not per-request
                except ImportError:
                    print(f"[{self.name}] aiohttp-socks not installed, skipping SOCKS proxy")
                    proxy_url = None
                    self.proxy = None

            self.session = aiohttp.ClientSession(
                headers=ua_rotator.get_headers(),
                timeout=aiohttp.ClientTimeout(total=30),
                connector=connector,
            )
    
    async def close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def fetch(self, url: str, retries=3):
        """Fetch URL with retries"""
        await self.init_session()
        
        for attempt in range(retries):
            try:
                await rate_limiter.wait_if_needed()
                await asyncio.sleep(rate_limiter.get_random_delay())
                
                async with self.session.get(url) as response:
                    if response.status == 200:
                        return await response.text()
            except Exception as e:
                print(f"Fetch error (attempt {attempt+1}): {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        return None
    
    async def parse(self):
        """Parse matches - override in subclass"""
        raise NotImplementedError("Subclasses must implement parse()")
    
    async def save_matches(self):
        """Save matches to database"""
        if not self.matches:
            return 0
        
        saved = 0
        for match in self.matches:
            match["home_team"] = team_normalizer.normalize(match.get("home_team", ""))
            match["away_team"] = team_normalizer.normalize(match.get("away_team", ""))
            date_str = str(match.get('match_time') or '')[:10]  # YYYY-MM-DD
            cache_key = f"match:{self.name}:{date_str}:{match.get('home_team')}:{match.get('away_team')}"
            cached = await cache.get(cache_key)
            
            if not cached:
                match["bookmaker"] = self.name
                match["parsed_at"] = datetime.utcnow().isoformat()
                
                if db.initialized:
                    await db.insert_match(match)
                
                await cache.set(cache_key, "1", expire=3600)
                saved += 1
        
        return saved
    
    async def run(self):
        """Run parser"""
        print(f"Starting {self.name} parser...")
        start_time = datetime.now()
        
        try:
            self.matches = await self.parse()
            saved_count = await self.save_matches()
            
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"{self.name} completed in {elapsed:.1f}s - {saved_count} matches")
            
            await telegram.send_parser_report(self.name, saved_count, "success")
            return saved_count
            
        except Exception as e:
            print(f"{self.name} failed: {e}")
            await telegram.send_alert_throttled(
                f"Parser Error: {self.name}", str(e),
                cooldown_key=f"parser_error:{self.name}",
                cooldown_seconds=1800
            )
            return 0
        
        finally:
            await self.close_session()
