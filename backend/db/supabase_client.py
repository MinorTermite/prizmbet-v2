# -*- coding: utf-8 -*-
"""Supabase Database Client"""
from supabase import create_client, Client
from backend.config import config

class Database:
    """Database client for Supabase"""
    
    def __init__(self):
        self.client = None
        self.initialized = False
    
    def init(self):
        """Initialize database connection"""
        if not self.initialized and config.SUPABASE_URL and config.SUPABASE_KEY:
            try:
                self.client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
                self.initialized = True
                print("Database connected")
            except Exception as e:
                print(f"Database connection failed: {e}")
                self.initialized = False
    
    async def insert_match(self, match_data: dict):
        """Insert a match into database"""
        if not self.initialized:
            return None
        try:
            response = self.client.table('matches').insert(match_data).execute()
            return response.data
        except Exception as e:
            print(f"Error inserting match: {e}")
            return None
    
    async def get_matches(self, sport='football', limit=100):
        """Get matches from database"""
        if not self.initialized:
            return []
        try:
            response = self.client.table('matches').select('*').eq('sport', sport).order('match_time', desc=False).limit(limit).execute()
            return response.data
        except Exception as e:
            print(f"Error fetching matches: {e}")
            return []
    
    async def log_parser_run(self, parser_name: str, status: str, matches_count: int = 0, error_message: str = None):
        """Log parser execution"""
        if not self.initialized:
            return
        try:
            self.client.table('parser_logs').insert({
                'parser_name': parser_name,
                'status': status,
                'matches_count': matches_count,
                'error_message': error_message
            }).execute()
        except Exception as e:
            print(f"Error logging parser run: {e}")

db = Database()
