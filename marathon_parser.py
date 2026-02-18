#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRIZMBET — Реальный парсер Marathonbet (playwright)
Источник: https://www.marathonbet.ru/su/betting/
URL матча: https://www.marathonbet.ru/su/betting/{path}/{eventId}

Установка:
  pip install playwright
  playwright install chromium
"""

from __future__ import annotations

import json
import os
import re
import sys
import io
import datetime
from typing import List

try:
    from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeoutError
except ImportError:
    print("ERROR: playwright не установлен. Выполните:")
    print("  pip install playwright && playwright install chromium")
    sys.exit(1)

# =============================================================================
# КОНФИГ
# =============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "matches_marathon.json")

MARATHON_BASE = "https://www.marathonbet.ru"

# Страницы по спортам — разделы предматчевой линии
SPORT_PAGES = [
    ("football",   "Футбол",       f"{MARATHON_BASE}/su/betting/Football/"),
    ("hockey",     "Хоккей",       f"{MARATHON_BASE}/su/betting/Ice+Hockey/"),
    ("basket",     "Баскетбол",    f"{MARATHON_BASE}/su/betting/Basketball/"),
    ("tennis",     "Теннис",       f"{MARATHON_BASE}/su/betting/Tennis/"),
    ("volleyball", "Волейбол",     f"{MARATHON_BASE}/su/betting/Volleyball/"),
    ("esports",    "Киберспорт",   f"{MARATHON_BASE}/su/betting/e-Sports/"),
    ("mma",        "Единоборства", f"{MARATHON_BASE}/su/betting/MMA/"),
]

PAGE_LOAD_MS = 6000
SCROLL_TIMES = 30
SCROLL_PX    = 700
SCROLL_WAIT  = 400

# =============================================================================
# JS — извлечение событий из DOM Marathonbet
# =============================================================================

EXTRACT_JS = r"""
() => {
    const BASE = 'https://www.marathonbet.ru';
    const results = [];
    const seenIds = new Set();

    // Основные контейнеры событий в Marathonbet
    const containers = document.querySelectorAll(
        '[data-event-id], [class*="coupon-row"], [class*="market-coupon-row"], ' +
        'tr[data-event-id], tr[id^="e"], [class*="event-row"]'
    );

    containers.forEach(el => {
        // Получаем event id
        let eventId = el.getAttribute('data-event-id')
                   || el.getAttribute('id')
                   || '';
        // Ищем числовой id
        const idMatch = eventId.match(/\d{5,}/);
        if (!idMatch) return;
        eventId = idMatch[0];
        if (seenIds.has(eventId)) return;
        seenIds.add(eventId);

        // Ссылка на матч
        let matchUrl = '';
        const linkEl = el.querySelector('a[href*="/su/betting/"]')
                    || el.querySelector('a[href*="/" ]');
        if (linkEl) {
            const href = linkEl.getAttribute('href') || '';
            matchUrl = href.startsWith('http') ? href : (BASE + href);
        }
        if (!matchUrl) {
            matchUrl = BASE + '/su/betting/' + eventId;
        }

        // Команды — ищем в специальных элементах Marathonbet
        let team1 = '', team2 = '';
        const participantEls = el.querySelectorAll(
            '[class*="member-name"], [class*="participant"], ' +
            '[class*="team-name"], [class*="player-name"]'
        );
        const teamTexts = [];
        participantEls.forEach(p => {
            const t = (p.innerText || p.textContent || '').trim();
            if (t && t.length > 1 && t.length < 80) teamTexts.push(t);
        });

        if (teamTexts.length >= 2) {
            team1 = teamTexts[0];
            team2 = teamTexts[1];
        } else {
            // Fallback: берём текст ссылки или элемента
            const fullText = (el.innerText || '').trim();
            // Пробуем разбить по "—" или " v "
            const sepMatch = fullText.match(/^(.+?)\s+[—\-–vs\.]+\s+(.+?)(?:\s+\d|$)/m);
            if (sepMatch) {
                team1 = sepMatch[1].trim();
                team2 = sepMatch[2].trim();
            }
        }

        if (!team1 || !team2 || team1 === team2) return;
        if (team1.length < 2 || team2.length < 2) return;

        // Убираем мусор (цифры дат, время) из имён команд
        const cleanTeam = s => s.replace(/\d{1,2}[:\-\.]\d{2}/, '').replace(/\d{1,2}\s+\w{2,4}/, '').trim();
        team1 = cleanTeam(team1);
        team2 = cleanTeam(team2);
        if (!team1 || !team2) return;

        // Коэффициенты — кнопки с числами
        const coefEls = el.querySelectorAll(
            '[class*="price"], [class*="coef"], [class*="odd"], ' +
            'button[class*="bet"], td[class*="coef"]'
        );
        const coefs = [];
        coefEls.forEach(c => {
            const t = (c.innerText || '').trim().replace(',', '.');
            if (/^\d+\.\d+$/.test(t) || /^\d+$/.test(t)) {
                const v = parseFloat(t);
                if (v >= 1.01 && v <= 100) coefs.push(t);
            }
        });

        const p1 = coefs[0] || '—';
        const x  = coefs[1] || '—';
        const p2 = coefs[2] || '—';

        // Дата/время
        let dateStr = '', timeStr = '';
        const elText = (el.innerText || '').replace(/\s+/g, ' ');
        const dtMatch = elText.match(/(\d{1,2})\s+(янв|фев|мар|апр|май|июн|июл|авг|сен|окт|ноя|дек)\s+(\d{1,2}:\d{2})/i);
        if (dtMatch) {
            dateStr = dtMatch[1] + ' ' + dtMatch[2].toLowerCase();
            timeStr = dtMatch[3];
        } else {
            const tmMatch = elText.match(/\b(\d{1,2}:\d{2})\b/);
            if (tmMatch) {
                timeStr = tmMatch[1];
                const now = new Date();
                const months = ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'];
                dateStr = now.getDate() + ' ' + months[now.getMonth()];
            }
        }

        // Лига из ближайшего заголовка
        let league = '';
        let parent = el.parentElement;
        for (let i = 0; i < 8 && parent; i++) {
            const hdr = parent.querySelector(
                '[class*="tournament-title"], [class*="category-title"], ' +
                '[class*="league-name"], [class*="championship-name"], h2, h3'
            );
            if (hdr) {
                league = (hdr.innerText || hdr.textContent || '').trim().split('\n')[0].trim();
                if (league && league.length > 2) break;
            }
            parent = parent.parentElement;
        }

        results.push({
            eventId,
            matchUrl,
            team1,
            team2,
            league: league || '',
            dateStr,
            timeStr,
            p1, x, p2,
        });
    });

    // Fallback: если ничего не нашли — ищем через ссылки событий
    if (results.length === 0) {
        const allLinks = document.querySelectorAll('a[href*="/su/betting/"]');
        const seenLinks = new Set();
        allLinks.forEach(link => {
            const href = link.getAttribute('href') || '';
            const idM = href.match(/\/(\d{7,})/);
            if (!idM) return;
            const eventId = idM[1];
            if (seenLinks.has(eventId)) return;
            seenLinks.add(eventId);

            const matchUrl = href.startsWith('http') ? href : (BASE + href);
            const lt = (link.innerText || link.textContent || '').trim();
            const parts = lt.split(/\n|—|–/).map(s => s.trim()).filter(Boolean);
            if (parts.length < 2) return;

            let card = link;
            for (let i = 0; i < 6; i++) {
                if (card.parentElement) card = card.parentElement;
                const cn = (card.className || '').toLowerCase();
                if (cn.includes('row') || cn.includes('event') || cn.includes('coupon')) break;
            }

            const coefEls = card.querySelectorAll('[class*="price"], [class*="coef"], button');
            const coefs = [];
            coefEls.forEach(c => {
                const t = (c.innerText || '').trim().replace(',', '.');
                if (/^\d+\.\d+$/.test(t)) {
                    const v = parseFloat(t);
                    if (v >= 1.01 && v <= 100) coefs.push(t);
                }
            });

            const elText = (card.innerText || '').replace(/\s+/g, ' ');
            let dateStr = '', timeStr = '';
            const dtMatch = elText.match(/(\d{1,2})\s+(янв|фев|мар|апр|май|июн|июл|авг|сен|окт|ноя|дек)\s+(\d{1,2}:\d{2})/i);
            if (dtMatch) {
                dateStr = dtMatch[1] + ' ' + dtMatch[2].toLowerCase();
                timeStr = dtMatch[3];
            }

            results.push({
                eventId,
                matchUrl,
                team1: parts[0],
                team2: parts[1],
                league: '',
                dateStr,
                timeStr,
                p1: coefs[0] || '—',
                x:  coefs[1] || '—',
                p2: coefs[2] || '—',
            });
        });
    }

    return results;
}
"""

# =============================================================================
# ОБРАБОТКА ДАННЫХ
# =============================================================================

def is_valid_coef(s: str) -> bool:
    try:
        v = float(str(s).replace(',', '.'))
        return 1.01 <= v <= 100.0
    except Exception:
        return False


def fmt_coef(s: str) -> str:
    if not s or s in ('—', '-', ''):
        return '—'
    s = str(s).strip()
    return s if is_valid_coef(s) else '—'


DATE_RX = r'\d{1,2}\s+[а-яёА-ЯЁa-zA-Z]{2,4}\s+\d{1,2}:\d{2}'


def clean_team(s: str) -> str:
    s = re.sub(DATE_RX, '', s)
    s = re.sub(r'^\W+|\W+$', '', s)
    return s.strip()


def process_raw(raw: dict, sport: str) -> dict | None:
    team1 = clean_team(raw.get('team1', ''))
    team2 = clean_team(raw.get('team2', ''))

    if not team1 or not team2 or team1 == team2:
        return None
    if len(team1) < 2 or len(team2) < 2:
        return None

    league = re.sub(r'\s+', ' ', raw.get('league', '')).strip()
    if len(league) < 2:
        league = sport.capitalize()

    match_url = raw.get('matchUrl', '') or raw.get('match_url', '')

    return {
        "sport":     sport,
        "league":    league,
        "id":        f"ma_{raw.get('eventId', '')}",
        "date":      raw.get('dateStr', ''),
        "time":      raw.get('timeStr', ''),
        "team1":     team1,
        "team2":     team2,
        "match_url": match_url,
        "p1":        fmt_coef(raw.get('p1', '')),
        "x":         fmt_coef(raw.get('x', '')),
        "p2":        fmt_coef(raw.get('p2', '')),
        "p1x":       "—",
        "p12":       "—",
        "px2":       "—",
        "source":    "marathon",
    }

# =============================================================================
# ПАРСЕР СТРАНИЦЫ
# =============================================================================

def scroll_and_load(page: Page) -> None:
    for _ in range(SCROLL_TIMES):
        page.evaluate(f"window.scrollBy(0, {SCROLL_PX})")
        page.wait_for_timeout(SCROLL_WAIT)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(400)
    for _ in range(SCROLL_TIMES // 2):
        page.evaluate(f"window.scrollBy(0, {SCROLL_PX * 2})")
        page.wait_for_timeout(350)


def parse_sport_page(page: Page, sport: str, url: str) -> List[dict]:
    print(f"  → {url}")
    try:
        page.goto(url, timeout=40_000, wait_until="domcontentloaded")
        page.wait_for_timeout(PAGE_LOAD_MS)
        scroll_and_load(page)
        page.wait_for_timeout(1500)
    except PWTimeoutError:
        print(f"    TIMEOUT: {url}")
        return []
    except Exception as e:
        print(f"    ERROR goto: {e}")
        return []

    try:
        raw_list = page.evaluate(EXTRACT_JS)
    except Exception as e:
        print(f"    ERROR evaluate: {e}")
        return []

    matches = []
    for raw in (raw_list or []):
        m = process_raw(raw, sport)
        if m:
            matches.append(m)

    print(f"    Матчей: {len(matches)}")
    return matches


# =============================================================================
# ГЛАВНЫЙ ПАРСЕР
# =============================================================================

def run_parser() -> List[dict]:
    all_matches: List[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
                "--disable-web-security",
                "--lang=ru-RU",
            ]
        )
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            viewport={"width": 1600, "height": 900},
        )
        page = ctx.new_page()

        def block_fn(route):
            url = route.request.url
            if any(x in url for x in [
                'adriver', 'yandex.ru/mc', 'mail.ru/counter',
                'doubleclick', 'adfox', 'rtb.', 'adspend',
                'bidvol', 'sbermarketing', 'beeline.ru',
            ]):
                route.abort()
            else:
                route.continue_()

        page.route("**/*", block_fn)

        for sport, label, url in SPORT_PAGES:
            print(f"\n[{label.upper()}]")
            try:
                matches = parse_sport_page(page, sport, url)
                all_matches.extend(matches)
            except Exception as e:
                print(f"  SKIP {label}: {e}")

        browser.close()

    return all_matches


# =============================================================================
# СОХРАНЕНИЕ (во временный файл, merge делает parse_all_real.py)
# =============================================================================

def save_matches(matches: List[dict]) -> None:
    seen: dict = {}
    for m in matches:
        k = m.get("id", "")
        if k and k not in seen:
            seen[k] = m
    unique = list(seen.values())

    data = {
        "last_update": datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "source": "marathonbet.ru",
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
    print("PRIZMBET — Парсер реальных матчей Marathonbet")
    print("Источник: marathonbet.ru")
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
