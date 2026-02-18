# PrizmBet v2 - Криптобукмекер с улучшенной архитектурой  
  
## ?? Новые возможности v2  
  
### Масштабируемость и Надёжность  
- ? **PostgreSQL (Supabase)** - бесплатная БД до 500MB  
- ? **Redis (Upstash)** - кэширование 10,000 команд/день  
- ? **Асинхронные парсеры** - быстрая параллельная загрузка  
- ? **Rate Limiting** - защита от блокировок  
- ? **Proxy Rotation** - обход блокировок букмекеров  
  
### Безопасность  
- ?? User-Agent ротация  
- ?? Экспоненциальная задержка при ошибках  
- ?? Автоматические retry при неудачах  
  
### Мониторинг  
- ?? Health check скрипт  
- ?? Telegram уведомления об ошибках  
- ?? Логирование всех запусков парсеров  
  
### UI/UX  
- ?? PWA (Progressive Web App)  
- ?? Тёмная тема  
- ?? Фильтрация и поиск на клиенте  
- ? Live-обновление коэффициентов  
  
## ?? Быстрый старт  
  
### 1. Клонирование  
```bash  
git clone https://github.com/YOUR_USERNAME/prizmbet-v2.git  
cd prizmbet-v2  
```  
  
### 2. Настройка переменных окружения  
```bash  
copy .env.example .env  
```  
  
Заполните `.env`:  
```  
SUPABASE_URL=your_supabase_url  
SUPABASE_KEY=your_supabase_key  
UPSTASH_REDIS_URL=your_upstash_url  
UPSTASH_REDIS_TOKEN=your_upstash_token  
TELEGRAM_BOT_TOKEN=your_bot_token  
TELEGRAM_CHAT_ID=your_chat_id  
```  
  
### 3. Установка зависимостей  
```bash  
pip install -r requirements.txt  
```  
  
### 4. Запуск  
```bash  
# Запуск всех парсеров  
python -m backend.run_parsers  
  
# Health check  
python -m backend.health_check  
```  
  
### Docker  
```bash  
# Сборка и запуск  
docker-compose up -d  
  
# Просмотр логов  
docker-compose logs -f parser  
```  
  
## ?? Настройка сервисов  
  
### Supabase (PostgreSQL)  
1. Зарегистрируйтесь на https://supabase.com  
2. Создайте новый проект  
3. В SQL Editor выполните скрипт из `config/supabase_schema.sql`  
4. Скопируйте URL и Key в `.env`  
  
### Upstash (Redis)  
1. Зарегистрируйтесь на https://upstash.com  
2. Создайте Redis базу  
3. Скопируйте URL и Token в `.env`  
  
### Telegram Bot  
1. Напишите @BotFather в Telegram  
2. Создайте бота командой /newbot  
3. Скопируйте токен в `.env`  
4. Узнайте свой chat_id через @userinfobot  
  
## ?? Структура проекта  
```  
prizmbet-v2/  
├── backend/  
│   ├── parsers/          # Парсеры букмекеров  
│   ├── db/               # Supabase клиент  
│   ├── utils/            # Утилиты (кэш, rate limiting)  
│   ├── api/              # API endpoints  
│   ├── config.py         # Конфигурация  
│   ├── health_check.py   # Проверка здоровья  
│   └── run_parsers.py    # Главный скрипт  
├── frontend/  
│   ├── css/              # Стили  
│   ├── js/               # JavaScript  
│   └── pwa/              # PWA файлы  
├── config/  
│   └── supabase_schema.sql  
├── tests/              # Тесты  
├── logs/               # Логи  
├── Dockerfile  
├── docker-compose.yml  
└── .github/workflows/    # CI/CD  
```  
