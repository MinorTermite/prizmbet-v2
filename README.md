# PrizmBet v2 - Crypto Betting Platform

## Features v2

### Scalability & Reliability
- PostgreSQL (Supabase) - Free DB up to 500MB
- Redis (Upstash) - 10,000 commands/day
- Async parsers - Fast parallel loading
- Rate Limiting - Protection from blocks
- Proxy Rotation - Bypass bookmaker blocks

### Security
- User-Agent rotation
- Exponential backoff on errors
- Automatic retries

### Monitoring
- Health check script
- Telegram error notifications
- Parser execution logs

### UI/UX
- PWA (Progressive Web App)
- Dark theme
- Client-side filtering
- Live odds updates

## Quick Start

### 1. Clone
```bash
git clone https://github.com/YOUR_USERNAME/prizmbet-v2.git
cd prizmbet-v2
```

### 2. Setup Environment
```bash
copy .env.example .env
```

Fill `.env`:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
UPSTASH_REDIS_URL=your_upstash_url
UPSTASH_REDIS_TOKEN=your_upstash_token
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run
```bash
# Run parsers
python -m backend.run_parsers

# Health check
python -m backend.health_check
```

### Docker
```bash
docker-compose up -d
docker-compose logs -f parser
```

## Setup Services

### Supabase
1. https://supabase.com - New Project
2. SQL Editor - run config/supabase_schema.sql
3. Settings - API - copy URL and Key

### Upstash Redis
1. https://upstash.com - Create Database
2. Copy URL and Token

### Telegram Bot
1. Message @BotFather on Telegram
2. Create bot with /newbot
3. Copy token to .env

## Project Structure
```
prizmbet-v2/
├── backend/
│   ├── parsers/
│   ├── db/
│   ├── utils/
│   ├── api/
│   └── config.py
├── frontend/
│   ├── css/
│   ├── js/
│   └── pwa/
├── config/
├── .github/workflows/
├── Dockerfile
└── docker-compose.yml
```
