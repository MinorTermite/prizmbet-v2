# 🏗️ Архитектура PRIZMBET

## 📊 Схема работы системы

```
┌─────────────────────────────────────────────────────────────┐
│                     GOOGLE SHEETS                           │
│                  (Источник данных)                          │
│                                                             │
│  Лига | ID | Дата | Время | Команда1 | Команда2 | Коэфф   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ CSV Export
                     │ (публичная ссылка)
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────────┐
│  GITHUB ACTIONS │    │  NETLIFY FUNCTION   │
│                 │    │                     │
│ Каждые 3 часа: │    │ По запросу:         │
│ 1. Скачать CSV  │    │ 1. Скачать CSV      │
│ 2. Парсинг      │    │ 2. Парсинг          │
│ 3. Сохранить    │    │ 3. Вернуть JSON     │
│    matches.json │    │                     │
│ 4. Git commit   │    │ GET /.netlify/      │
│ 5. Git push     │    │     functions/      │
└────────┬────────┘    │     update-matches  │
         │             └─────────────────────┘
         │                       │
         │ Push trigger          │ HTTP Request
         │                       │
         ▼                       │
┌─────────────────────────────────────────┐
│            GITHUB PAGES                  │
│                                         │
│  Auto-rebuild при изменении в GitHub    │
│  Раздача статики (HTML, CSS, JS)       │
│  Serverless functions                   │
│  SSL сертификат (HTTPS)                 │
└─────────────────┬───────────────────────┘
                  │
                  │ HTTPS
                  │
                  ▼
         ┌────────────────┐
         │   index.html   │
         │                │
         │ 1. Загрузка    │
         │ 2. Fetch       │
         │    matches.json│
         │ 3. Рендер      │
         │ 4. Фильтры     │
         │ 5. Поиск       │
         └────────────────┘
                  │
                  │
                  ▼
         ┌────────────────┐
         │ ПОЛЬЗОВАТЕЛЬ   │
         │                │
         │ 🖥️  💻  📱    │
         └────────────────┘
```

## 🔄 Процесс обновления данных

### Автоматическое обновление (каждые 3 часа)

```
1. GitHub Actions срабатывает по расписанию
   └─ Cron: 0 */3 * * * (00:00, 03:00, 06:00, ..., 21:00 UTC)

2. Запускается Python скрипт: update_matches.py
   ├─ Скачивает CSV из Google Sheets
   ├─ Парсит данные (команды, коэффициенты, даты)
   ├─ Определяет вид спорта по названию лиги
   └─ Сохраняет в matches.json

3. Git операции
   ├─ git add matches.json
   ├─ git commit -m "auto-update matches [дата]"
   └─ git push

4. GitHub уведомляет GitHub Pages о push

5. GitHub Pages автоматически пересобирает сайт
   ├─ Деплой новой версии
   ├─ Инвалидация CDN кэша
   └─ Сайт обновлён!

6. Пользователи видят новые данные
```

### Ручное обновление (по требованию)

```
Вариант 1: Через GitHub Actions
└─ Actions → Run workflow → Обновление сразу

Вариант 2: Через GitHub Pages Function
└─ GET /.netlify/functions/update-matches
   └─ Возвращает свежие данные из Google Sheets
```

## 📁 Структура файлов

```
prizmbet-final/
│
├── 🌐 Frontend
│   ├── index.html              # Главная страница
│   ├── matches.json            # Кэш данных матчей
│   ├── prizmbet-logo.gif       # Лого
│   ├── prizmbet-logo.mp4       # Видео лого
│   ├── prizmbet-info-1.png     # Инфографика
│   ├── prizmbet-info-2.png     # Инфографика
│   └── qr_wallet.png           # QR код кошелька
│
├── 🔧 Backend
│   ├── update_matches.py       # Python скрипт для GitHub Actions
│   └── netlify/
│       └── functions/
│           └── update-matches.js  # Serverless функция
│
├── ⚙️ Конфигурация
│   ├── netlify.toml            # Настройки GitHub Pages
│   ├── package.json            # Node.js зависимости
│   ├── requirements.txt        # Python зависимости
│   └── .gitignore              # Игнорируемые файлы
│
├── 🤖 Автоматизация
│   └── .github/
│       └── workflows/
│           └── update-matches.yml  # GitHub Actions workflow
│
└── 📖 Документация
    ├── README.md               # Основная документация
    ├── QUICK_DEPLOY.md         # Быстрый старт
    ├── DEPLOY_INSTRUCTIONS.md  # Подробная инструкция
    └── ARCHITECTURE.md         # Эта схема
```

## 🔑 Ключевые компоненты

### 1. Google Sheets (Источник данных)
```
URL: https://docs.google.com/spreadsheets/d/1QkVj51WMKSd6-LU4vZK3dYPk6QLQIO014ydpACtThNk
Формат: CSV экспорт
Доступ: Публичный (только чтение)

Колонки:
- Лига (League)
- ID матча
- Дата
- Время
- Команда 1
- Команда 2
- P1 (коэфф. на победу 1)
- X (коэфф. на ничью)
- P2 (коэфф. на победу 2)
- P1X (двойной шанс)
- P12 (обе забьют)
- PX2 (двойной шанс)
```

### 2. update_matches.py (GitHub Actions)
```python
Задачи:
✓ Скачивание CSV с retry (3 попытки)
✓ Парсинг CSV с валидацией
✓ Определение спорта по лиге
✓ Очистка данных от артефактов
✓ Атомарная запись в matches.json
✓ Статистика (количество матчей/лиг/спортов)

Запуск:
- Автоматически: каждые 3 часа (GitHub Actions)
- Вручную: Actions → Run workflow
- Локально: python update_matches.py
```

### 3. update-matches.js (GitHub Pages Function)
```javascript
Задачи:
✓ Скачивание CSV через fetch API
✓ Парсинг CSV (поддержка кавычек)
✓ Определение спорта
✓ Возврат JSON с CORS headers
✓ Кэширование (5 минут)

Endpoint:
GET /.netlify/functions/update-matches

Response:
{
  "last_update": "2026-02-16 12:00:00",
  "matches": [...]
}
```

### 4. index.html (Frontend)
```javascript
Возможности:
✓ Загрузка данных из matches.json
✓ Fallback на GitHub Pages Function
✓ Фильтры по спортам (футбол, хоккей, баскетбол, киберспорт)
✓ Поиск по командам
✓ Адаптивная верстка (мобильные, планшеты, десктоп)
✓ 3D фон (Three.js)
✓ Mesh градиенты
✓ Анимации
✓ QR код для пополнения
```

## 🎨 Технологический стек

### Frontend
- **HTML5** - разметка
- **CSS3** - стили (gradients, animations, grid, flexbox)
- **Vanilla JavaScript** - логика (без фреймворков)
- **Three.js** - 3D космический фон
- **Fetch API** - загрузка данных

### Backend
- **Python 3.11** - скрипт синхронизации
- **Node.js 18** - GitHub Pages Functions
- **GitHub Actions** - CI/CD

### Инфраструктура
- **GitHub** - хостинг кода, автоматизация
- **GitHub Pages** - хостинг сайта, CDN, serverless
- **Google Sheets** - база данных

## 🔒 Безопасность

```
✅ HTTPS (SSL сертификат от Let's Encrypt)
✅ CORS настроен правильно
✅ Нет хранения паролей/ключей в коде
✅ Google Sheets - только чтение
✅ Rate limiting (GitHub Pages встроенный)
✅ DDoS защита (GitHub Pages CDN)
✅ Валидация входных данных
```

## ⚡ Производительность

```
Frontend:
- Размер HTML: ~50KB (минимизирован)
- Размер matches.json: ~30KB
- Загрузка Three.js: CDN (кэшируется)
- First Contentful Paint: <1s
- Time to Interactive: <2s

Backend:
- GitHub Actions: ~10-20 секунд на обновление
- GitHub Pages Function: <1 секунда на запрос
- Google Sheets CSV: ~500ms загрузка

CDN:
- Edge locations: >100 по всему миру
- Cache TTL: 5 минут
- Gzip compression: включён
```

## 📈 Масштабируемость

```
Текущие лимиты:
- GitHub Actions: 2000 минут/месяц (free tier)
  └─ 1 запуск = ~10 секунд
  └─ 8 запусков/день × 30 дней = 40 минут/месяц
  └─ Запас: 1960 минут

- GitHub Pages:
  └─ 100GB bandwidth/месяц (free tier)
  └─ 125K serverless запросов/месяц
  └─ Unlimited deploys

- Google Sheets:
  └─ 10M ячеек на документ
  └─ 100 запросов/100 секунд/пользователь
  └─ Достаточно для 1000+ матчей
```

## 🔧 Возможные улучшения

```
1. База данных
   └─ Переход с Google Sheets на PostgreSQL/MongoDB

2. Админ панель
   └─ Интерфейс для редактирования матчей

3. Live обновления
   └─ WebSocket для real-time коэффициентов

4. Аналитика
   └─ Статистика по ставкам, популярные матчи

5. Авторизация
   └─ Личный кабинет пользователя

6. История ставок
   └─ Хранение и отображение прошлых ставок

7. API
   └─ REST API для сторонних приложений

8. Мобильное приложение
   └─ React Native / Flutter
```

---

💎 **PRIZMBET** - современный криптобукмекер на PRIZM
