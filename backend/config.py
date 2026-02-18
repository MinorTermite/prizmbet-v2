# -*- coding: utf-8 -*-
"""PrizmBet v2 Configuration"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration class"""
    
    # Supabase
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
    
    # Redis (Upstash)
    UPSTASH_REDIS_URL = os.getenv('UPSTASH_REDIS_URL', '')
    UPSTASH_REDIS_TOKEN = os.getenv('UPSTASH_REDIS_TOKEN', '')
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Parser Settings
    PROXY_ENABLED = os.getenv('PROXY_ENABLED', 'false').lower() == 'true'
    RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', '10'))
    RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '60'))
    
    # GitHub
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')

config = Config()
