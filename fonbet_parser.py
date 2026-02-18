#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRIZMBET — Парсер реальных матчей Fonbet
Источник: https://www.fonbet.ru/sports/
API: https://line91.bkfon-resource.com/live/currentLine/ru
URL матча: https://www.fonbet.ru/sports/{sport}/{eventId}/

Установка:
  pip install requests
"""

from __future__ import annotations

import json
import os
import sys
import io
import datetime
import time
import re
from typing import List

try:
    import requests
except ImportError:
    print("ERROR: requests не установлен. Выполните: pip install requests")
    sys.exit(1)

# =============================================================================
# КОНФИГ
# =============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "matches.json")

FONBET_BASE = "https://www.fonbet.ru"

# Fonbet публичное API для предматчевой линии
LINE_API_URL = "https://line91.bkfon-resource.com/live/currentLine/ru"

# Маппинг Fonbet sportId -> наш sport slug
SPORT_MAP = {
    1:  "football",
    2:  "hockey",
    3:  "basket",
    4:  "tennis",
    5:  "volleyball",
    6:  "mma",          # единоборства
    21: "esports",      # киберспорт
    40: "mma",          # бокс
    41: "mma",          # MMA
}

# Только эти виды спорта
ALLOWED_SPORTS = set(SPORT_MAP.values())

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9",
    "Referer": "https://www.fonbet.ru/",
    "Origin": "https://www.fonbet.ru",
}

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def fmt_date(ts: int | None) -> tuple[str, str]:
    """Timestamp -> ('18 фев', '20:00')"""
    if not ts:
        return '', ''
    months = ['янв','фев','мар','апр','май','июн',
              'июл','авг','сен','окт','ноя','дек']
    dt = datetime.datetime.fromtimestamp(ts)
    date_str = f"{dt.day} {months[dt.month - 1]}"
    time_str = dt.strftime("%H:%M")
    return date_str, time_str


def fmt_coef(val) -> str:
    """Числовой коэффициент -> строка, либо '—'"""
    try:
        v = float(val)
        if 1.01 <= v <= 100.0:
            return f"{v:.2f}"
    except Exception:
        pass
    return '—'


def build_match_url(sport_slug: str, event_id) -> str:
    return f"{FONBET_BASE}/sports/{sport_slug}/{event_id}/"


# =============================================================================
# ПОЛУЧЕНИЕ ДАННЫХ ОТ FONBET API
# =============================================================================

def fetch_line_data() -> dict | None:
    """Загружает текущую линию Fonbet."""
    params = {
        "sysId": "1",
        "place": "1",
    }
    try:
        resp = requests.get(
            LINE_API_URL,
            params=params,
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        print(f"  HTTP ERROR: {e}")
        return None
    except Exception as e:
        print(f"  ERROR fetch_line_data: {e}")
        return None


# =============================================================================
# ПАРСИНГ СОБЫТИЙ
# =============================================================================

def extract_factor(factors: list, tag: int) -> str:
    """Ищет коэффициент по тегу из списка факторов."""
    for f in factors:
        if f.get('f') == tag:
            return fmt_coef(f.get('v', ''))
    return '—'


def parse_events(data: dict) -> List[dict]:
    """Парсит события из ответа Fonbet API."""
    matches = []

    if not data:
        return matches

    events = data.get('events', [])
    factors_map: dict[int, list] = {}
    # Индексируем факторы по eventId
    for ev_factors in data.get('eventFactors', []):
        eid = ev_factors.get('e')
        if eid:
            factors_map.setdefault(eid, []).append(ev_factors)

    # Индекс родительских событий (турниров/лиг)
    parent_map: dict[int, dict] = {}
    for ev in events:
        ev_id = ev.get('id')
        if ev_id:
            parent_map[ev_id] = ev

    seen_ids: set = set()

    for ev in events:
        # Только матчи (не турниры), kind=1 — спортивное событие
        if ev.get('kind') != 1:
            continue

        sport_id = ev.get('sportId', 0)
        sport_slug = SPORT_MAP.get(sport_id)
        if not sport_slug:
            continue

        event_id = ev.get('id')
        if not event_id or event_id in seen_ids:
            continue
        seen_ids.add(event_id)

        # Название события: "Команда1 — Команда2"
        name = ev.get('name', '')
        if ' — ' in name:
            parts = name.split(' — ', 1)
            team1 = parts[0].strip()
            team2 = parts[1].strip()
        elif ' - ' in name:
            parts = name.split(' - ', 1)
            team1 = parts[0].strip()
            team2 = parts[1].strip()
        else:
            # Пропустить если не удалось разбить на команды
            continue

        if not team1 or not team2 or len(team1) < 2 or len(team2) < 2:
            continue

        # Лига / чемпионат
        parent_id = ev.get('parentId')
        league = ''
        if parent_id and parent_id in parent_map:
            parent = parent_map[parent_id]
            league = parent.get('name', '')
            # Иногда нужен дедушка
            if not league or len(league) < 2:
                grandpa_id = parent.get('parentId')
                if grandpa_id and grandpa_id in parent_map:
                    league = parent_map[grandpa_id].get('name', '')

        league = re.sub(r'\s+', ' ', league).strip()
        if not league or len(league) < 2:
            league = name  # запасной вариант

        # Дата/время
        start_ts = ev.get('startTime', ev.get('start', 0))
        if isinstance(start_ts, str):
            # ISO формат "2026-02-18T20:00:00"
            try:
                dt = datetime.datetime.fromisoformat(start_ts)
                start_ts = int(dt.timestamp())
            except Exception:
                start_ts = 0
        date_str, time_str = fmt_date(start_ts)

        # Коэффициенты — ищем факторы для этого события
        ev_factors = factors_map.get(event_id, [])
        # Теги Fonbet: 921=П1, 922=X, 923=П2 (основной тотал 1x2)
        p1 = extract_factor(ev_factors, 921)
        x  = extract_factor(ev_factors, 922)
        p2 = extract_factor(ev_factors, 923)

        match_url = build_match_url(sport_slug, event_id)

        matches.append({
            "sport":     sport_slug,
            "league":    league,
            "id":        str(event_id),
            "date":      date_str,
            "time":      time_str,
            "team1":     team1,
            "team2":     team2,
            "match_url": match_url,
            "p1":        p1,
            "x":         x,
            "p2":        p2,
            "p1x":       "—",
            "p12":       "—",
            "px2":       "—",
        })

    return matches


# =============================================================================
# ГЛАВНЫЙ ПАРСЕР
# =============================================================================

def run_parser() -> List[dict]:
    print("Загрузка линии Fonbet...")
    data = fetch_line_data()
    if not data:
        print("  ERROR: данные не получены")
        return []

    matches = parse_events(data)
    print(f"  Матчей найдено: {len(matches)}")
    return matches


# =============================================================================
# СОХРАНЕНИЕ (merge с winline)
# =============================================================================

def save_matches(matches: List[dict]) -> None:
    # Дедупликация
    seen: dict = {}
    for m in matches:
        k = m.get("id", "")
        if k and k not in seen:
            seen[k] = m
    unique = list(seen.values())

    months = {'янв':'01','фев':'02','мар':'03','апр':'04','май':'05','июн':'06',
              'июл':'07','авг':'08','сен':'09','окт':'10','ноя':'11','дек':'12'}

    def sort_key(m):
        d = m.get('date', '')
        t = m.get('time', '')
        parts = d.split()
        if len(parts) == 2:
            return f"{months.get(parts[1].lower(),'01')}-{parts[0].zfill(2)} {t}"
        return f"99-99 {t}"

    unique.sort(key=sort_key)

    data = {
        "last_update": datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "source": "fonbet.ru",
        "matches": unique,
    }

    tmp = OUTPUT_FILE + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    if os.path.exists(OUTPUT_FILE):
        os.replace(tmp, OUTPUT_FILE)
    else:
        os.rename(tmp, OUTPUT_FILE)

    kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"\n✓ Сохранено: {OUTPUT_FILE} ({kb:.1f} KB)")
    print(f"✓ Всего матчей: {len(unique)}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 60)
    print("PRIZMBET — Парсер реальных матчей Fonbet")
    print("Источник: fonbet.ru")
    print("=" * 60)

    matches = run_parser()

    if not matches:
        print("\nERROR: матчи не найдены")
        sys.exit(1)

    save_matches(matches)

    from collections import Counter
    sports = Counter(m['sport'] for m in matches)
    print("\nПо видам спорта:")
    for s, c in sorted(sports.items(), key=lambda x: -x[1]):
        print(f"  {s}: {c}")

    print("\n" + "=" * 60)
    print("ГОТОВО")


if __name__ == "__main__":
    main()
