#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRIZMBET - Единый скрипт синхронизации данных из Google Sheets
Используется в GitHub Actions и для локального запуска
"""

import json
import datetime
import re
import csv
import urllib.request
import sys
import io
import os

# КОНФИГУРАЦИЯ
SHEET_ID = os.getenv("SHEET_ID", "1QkVj51WMKSd6-LU4vZK3dYPk6QLQIO014ydpACtThNk")
GID = os.getenv("SHEET_GID", "0")
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
OUTPUT_FILE = "matches.json"

# Маппинг спортов по началу названия лиги
SPORT_MAPPING = {
    # ── FOOTBALL ──────────────────────────────────────────────
    'Лига чемпионов УЕФА': 'football',
    'Лига Европы УЕФА': 'football',
    'Лига конференций УЕФА': 'football',
    'УЕФА': 'football',
    'UEFA': 'football',
    'Англия. Премьер-лига': 'football',
    'Англия. Чемпионшип': 'football',
    'Англия. Лига 1': 'football',
    'Англия. Лига 2': 'football',
    'Англия. Кубок': 'football',
    'Англия. Кубок Лиги': 'football',
    'Испания. Ла Лига': 'football',
    'Испания. Сегунда': 'football',
    'Испания. Кубок Короля': 'football',
    'Германия. Бундеслига': 'football',
    'Германия. 2. Бундеслига': 'football',
    'Германия. Кубок': 'football',
    'Италия. Серия A': 'football',
    'Италия. Серия B': 'football',
    'Итальянский. Кубок': 'football',
    'Франция. Лига 1': 'football',
    'Франция. Лига 2': 'football',
    'Россия. Премьер-лига': 'football',
    'Россия. ФНЛ': 'football',
    'Россия. Кубок': 'football',
    'Нидерланды. Эредивизие': 'football',
    'Португалия. Примейра Лига': 'football',
    'Турция. Суперлига': 'football',
    'Шотландия. Премьершип': 'football',
    'Бельгия. Про Лига': 'football',
    'Бразилия. Серия A': 'football',
    'Аргентина. Примера Дивисьон': 'football',
    'США. MLS': 'football',
    'MLS': 'football',
    'Мексика. Лига MX': 'football',
    'КОНМЕБОЛ. Копа Либертадорес': 'football',
    'КОНКАКАФ': 'football',
    'Саудовская Аравия. Про Лига': 'football',
    'Япония. Джей-Лига': 'football',
    'Южная Корея. К-Лига': 'football',
    'Австралия. A-League': 'football',
    'Африка. КАФ': 'football',
    'Азия. AFC': 'football',
    'Греция. Суперлига': 'football',
    'Украина. Премьер-лига': 'football',
    'Польша. Экстракласа': 'football',
    'Чехия. Первая лига': 'football',
    'Австрия. Бундеслига': 'football',
    'Швейцария. Суперлига': 'football',
    'Дания. Суперлига': 'football',
    'Норвегия. Элитесерия': 'football',
    'Швеция. Алльсвенскан': 'football',
    # ── HOCKEY ────────────────────────────────────────────────
    'КХЛ': 'hockey',
    'НХЛ': 'hockey',
    'NHL': 'hockey',
    'ВХЛ': 'hockey',
    'МХЛ': 'hockey',
    'AHL': 'hockey',
    'ECHL': 'hockey',
    'Швеция. SHL': 'hockey',
    'Финляндия. Liiga': 'hockey',
    'Чехия. Extraliga': 'hockey',
    'Германия. DEL': 'hockey',
    'Швейцария. National League': 'hockey',
    'Беларусь. Экстралига': 'hockey',
    'Казахстан. ЧРК': 'hockey',
    'Австрия. ICEHL': 'hockey',
    'Словакия. Extraliga': 'hockey',
    # ── BASKETBALL ────────────────────────────────────────────
    'NBA': 'basket',
    'НБА': 'basket',
    'Евролига': 'basket',
    'EuroLeague': 'basket',
    'EuroCup': 'basket',
    'Единая лига ВТБ': 'basket',
    'Испания. ACB': 'basket',
    'Турция. BSL': 'basket',
    'Италия. LBA': 'basket',
    'Франция. Про A': 'basket',
    'Германия. BBL': 'basket',
    'Греция. HEBA A1': 'basket',
    'Израиль. Winner League': 'basket',
    'Австралия. NBL': 'basket',
    'Китай. CBA': 'basket',
    'ФИБА': 'basket',
    'FIBA': 'basket',
    # ── ESPORTS ───────────────────────────────────────────────
    'CS2': 'esports',
    'Counter-Strike': 'esports',
    'Dota 2': 'esports',
    'Valorant': 'esports',
    'League of Legends': 'esports',
    'LoL': 'esports',
    'Rocket League': 'esports',
    'RLCS': 'esports',
    'Overwatch': 'esports',
    'PUBG': 'esports',
    'Apex Legends': 'esports',
    'Rainbow Six': 'esports',
    'Hearthstone': 'esports',
    'StarCraft': 'esports',
    # ── TENNIS ────────────────────────────────────────────────
    'ATP': 'tennis',
    'WTA': 'tennis',
    'ITF': 'tennis',
    'Теннис': 'tennis',
    # ── VOLLEYBALL ────────────────────────────────────────────
    'CEV': 'volleyball',
    'ВНЛ': 'volleyball',
    'VNL': 'volleyball',
    'Россия. Суперлига': 'volleyball',
    'Польша. PlusLiga': 'volleyball',
    'Италия. SuperLega': 'volleyball',
    'Волейбол': 'volleyball',
    # ── MMA ───────────────────────────────────────────────────
    'UFC': 'mma',
    'Bellator': 'mma',
    'ONE Championship': 'mma',
    'ONE FC': 'mma',
    'ACB MMA': 'mma',
    'PFL': 'mma',
    'M-1': 'mma',
    'Absolute Championship': 'mma',
}

def norm(s):
    """Нормализация строки"""
    return (s or "").strip()

def detect_sport(league):
    """Определение спорта по названию лиги"""
    for key, sport in SPORT_MAPPING.items():
        if league.startswith(key):
            return sport
    ll = league.lower()
    if any(k in ll for k in ['футбол', 'лига', 'премьер', 'кубок', 'уефа', 'серия', 'бундес', 'ла лига', 'копа', 'mls']):
        return 'football'
    if any(k in ll for k in ['хоккей', 'кхл', 'нхл', 'hockey', 'nhl', 'ahl', 'shl', 'liiga', 'del']):
        return 'hockey'
    if any(k in ll for k in ['баскет', 'nba', 'евролига', 'basketball', 'vtb', 'acb', 'bbl']):
        return 'basket'
    if any(k in ll for k in ['dota', 'cs2', 'counter-strike', 'valorant', 'esports', 'rlcs', 'pubg', 'apex']):
        return 'esports'
    if any(k in ll for k in ['теннис', 'atp', 'wta', 'itf', 'уимблдон', 'ролан гаррос', 'открытый чемпионат']):
        return 'tennis'
    if any(k in ll for k in ['волейбол', 'volleyball', 'суперлига', 'cev', 'vnl', 'plusliga', 'superlega']):
        return 'volleyball'
    if any(k in ll for k in ['ufc', 'bellator', 'mma', 'one championship', 'pfl', 'acb']):
        return 'mma'
    return 'football'

def download_csv():
    """Скачивание CSV из Google Sheets с retry"""
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[{attempt}/{max_retries}] Loading data from Google Sheets...")
            req = urllib.request.Request(CSV_URL, headers={
                'User-Agent': 'Mozilla/5.0 PRIZMBET-Bot/1.0'
            })
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read().decode('utf-8')
            if content.strip():
                print(f"OK: loaded {len(content)} bytes")
                return content
            print("WARNING: empty response")
        except Exception as e:
            print(f"ERROR attempt {attempt}: {e}")
            if attempt == max_retries:
                return None
            import time
            time.sleep(5 * attempt)
    return None

def parse_csv_content(csv_content):
    """Парсинг CSV и создание списка матчей"""
    matches = []
    lines = csv_content.strip().split('\n')
    reader = csv.reader(lines)
    header = next(reader, None)

    if header:
        print(f"Columns: {len(header)} -> {header[:6]}...")

    row_num = 0
    skipped = 0

    for row in reader:
        row_num += 1
        if len(row) < 12:
            skipped += 1
            continue

        league = norm(row[0])
        match_id = norm(row[1])
        date = norm(row[2])
        time_val = norm(row[3])
        team1 = norm(row[4])
        team2 = norm(row[5])

        if not league or not team1 or not team2:
            skipped += 1
            continue

        # Очистка: иногда дата/время попадает в имя команды
        # Regex поддерживает кириллические месяцы: "17 фев 20:45", "1 янв 10:00"
        DATE_TIME_RX = r'\d{1,2}\s+[а-яёА-ЯЁa-zA-Z]{2,4}\s+\d{1,2}:\d{2}'
        team1 = re.sub(DATE_TIME_RX, '', team1).strip()
        team2 = re.sub(DATE_TIME_RX, '', team2).strip()

        if not team1 or not team2:
            skipped += 1
            continue

        p1 = norm(row[6]) or "0.00"
        x = norm(row[7]) or "0.00"
        p2 = norm(row[8]) or "0.00"
        p1x = norm(row[9]) or "0.00"
        p12 = norm(row[10]) or "0.00"
        px2 = norm(row[11]) or "0.00"
        # Необязательное поле match_url (колонка 12, если есть)
        match_url = norm(row[12]) if len(row) > 12 else ""

        sport = detect_sport(league)

        entry = {
            "sport": sport,
            "league": league,
            "id": match_id,
            "date": date,
            "time": time_val,
            "team1": team1,
            "team2": team2,
            "p1": p1,
            "x": x,
            "p2": p2,
            "p1x": p1x,
            "p12": p12,
            "px2": px2,
        }
        if match_url:
            entry["match_url"] = match_url
        matches.append(entry)

    print(f"Parsed {len(matches)} matches from {row_num} rows (skipped {skipped})")
    return matches

def save_matches(matches):
    """Атомарное сохранение matches.json"""
    data = {
        "last_update": datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "matches": matches
    }

    tmp_file = OUTPUT_FILE + ".tmp"
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Атомарная замена
    if os.path.exists(OUTPUT_FILE):
        os.replace(tmp_file, OUTPUT_FILE)
    else:
        os.rename(tmp_file, OUTPUT_FILE)

    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"Saved {OUTPUT_FILE} ({size_kb:.1f} KB)")

def print_stats(matches):
    """Вывод статистики"""
    sports = {}
    leagues = {}
    for m in matches:
        sports[m['sport']] = sports.get(m['sport'], 0) + 1
        leagues[m['league']] = leagues.get(m['league'], 0) + 1

    print(f"\nTotal: {len(matches)} matches, {len(leagues)} leagues")
    for sport, count in sorted(sports.items()):
        print(f"  {sport}: {count}")

def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 60)
    print("PRIZMBET - Google Sheets Sync")
    print("=" * 60)

    csv_content = download_csv()
    if not csv_content:
        print("FATAL: Could not download data from Google Sheets")
        sys.exit(1)

    matches = parse_csv_content(csv_content)
    if not matches:
        print("FATAL: No matches parsed from CSV")
        sys.exit(1)

    save_matches(matches)
    print_stats(matches)
    print("=" * 60)
    print("SYNC OK")

if __name__ == "__main__":
    main()
