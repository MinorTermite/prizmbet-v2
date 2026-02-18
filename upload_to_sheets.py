#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRIZMBET — Upload real matches to Google Sheets
Sources: winline.ru + marathonbet.ru

Столбцы в таблице:
  Спорт | Лига | Дата | Время | Команда 1 | Команда 2 | К1 | X | К2 | Winline | Marathon

Ссылки:
  - Winline: https://winline.ru/stavki/event/{id}   (из поля match_url)
  - Marathon: https://marathonbet.ru/...              (из поля match_url_marathon, если есть)
"""

import json
import os
import sys
import io
import gspread
from google.oauth2.service_account import Credentials

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MATCHES_FILE = os.path.join(SCRIPT_DIR, 'matches.json')
CREDS_FILE = os.path.join(SCRIPT_DIR, 'credentials.json')
SPREADSHEET_ID = '1QkVj51WMKSd6-LU4vZK3dYPk6QLQIO014ydpACtThNk'

WINLINE_BASE  = 'https://winline.ru/stavki/event/'
MARATHON_BASE = 'https://www.marathonbet.ru/su/betting/'


def get_winline_url(m: dict) -> str:
    """Возвращает прямую ссылку на матч в Winline."""
    url = m.get('match_url', '')
    if url and 'winline' in url:
        return url
    # Для матчей из winline id не имеет префикса
    match_id = m.get('id', '')
    src = m.get('source', '')
    if src == 'winline' and match_id:
        return f"{WINLINE_BASE}{match_id}"
    if url and url.startswith('http') and 'winline' in url:
        return url
    # winline матч — id без префикса ma_
    if match_id and not match_id.startswith('ma_'):
        return f"{WINLINE_BASE}{match_id}"
    return ''


def get_marathon_url(m: dict) -> str:
    """Возвращает прямую ссылку на матч в Marathonbet."""
    # Явное поле от marathon парсера
    url = m.get('match_url_marathon', '')
    if url and url.startswith('http'):
        return url
    # Если матч пришёл из marathon
    src = m.get('source', '')
    match_url = m.get('match_url', '')
    if src == 'marathon' and match_url and match_url.startswith('http'):
        return match_url
    if 'marathonbet' in match_url:
        return match_url
    # Строим из id если префикс ma_
    match_id = m.get('id', '')
    if match_id.startswith('ma_'):
        raw_id = match_id[3:]
        return f"{MARATHON_BASE}{raw_id}"
    return ''


def main():
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 60)
    print("PRIZMBET — Upload to Google Sheets")
    print("Sources: winline.ru + marathonbet.ru")
    print("=" * 60)

    # Credentials
    print("\nLoading credentials...")
    creds = Credentials.from_service_account_file(
        CREDS_FILE,
        scopes=[
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive',
        ]
    )
    print(f"[OK] Service Account: {creds.service_account_email}")

    # Open spreadsheet
    print(f"\nOpening spreadsheet {SPREADSHEET_ID}...")
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(SPREADSHEET_ID)
    worksheet = sheet.get_worksheet(0)
    print(f"[OK] Worksheet: {worksheet.title}")

    # Load matches
    print(f"\nLoading {MATCHES_FILE}...")
    with open(MATCHES_FILE, encoding='utf-8') as f:
        data = json.load(f)
    matches = data.get('matches', [])
    last_update = data.get('last_update', '')
    source = data.get('source', '')
    print(f"[OK] Matches: {len(matches)} | Updated: {last_update}")
    print(f"[OK] Source: {source}")

    # Header
    header = [
        'Спорт', 'Лига', 'Дата', 'Время',
        'Команда 1', 'Команда 2',
        'К1', 'X', 'К2',
        'Winline (ссылка)', 'Marathon (ссылка)',
    ]

    rows = [header]
    no_winline = 0
    no_marathon = 0

    for m in matches:
        wl_url = get_winline_url(m)
        ma_url = get_marathon_url(m)

        if not wl_url:
            no_winline += 1
        if not ma_url:
            no_marathon += 1

        rows.append([
            m.get('sport', ''),
            m.get('league', ''),
            m.get('date', ''),
            m.get('time', ''),
            m.get('team1', ''),
            m.get('team2', ''),
            m.get('p1', '—'),
            m.get('x', '—'),
            m.get('p2', '—'),
            wl_url,
            ma_url,
        ])

    print(f"\n  Матчей без Winline ссылки: {no_winline}")
    print(f"  Матчей без Marathon ссылки: {no_marathon}")

    # Upload
    print(f"\nClearing worksheet...")
    worksheet.clear()
    print(f"Uploading {len(rows) - 1} rows...")
    worksheet.update('A1', rows, value_input_option='RAW')

    print("\n" + "=" * 60)
    print(f"[OK] SUCCESS: {len(rows) - 1} matches uploaded")
    print(f"[URL] https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    print("=" * 60)


if __name__ == "__main__":
    main()
