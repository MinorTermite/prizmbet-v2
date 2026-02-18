#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRIZMBET — Реальный парсер Winline (playwright)
Источник: https://winline.ru/stavki
URL каждого матча: https://winline.ru/stavki/event/{eventId}

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
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "matches.json")

WINLINE_BASE = "https://winline.ru"

SPORT_PAGES = [
    ("football",   "футбол",      f"{WINLINE_BASE}/stavki/sport/futbol"),
    ("hockey",     "хоккей",      f"{WINLINE_BASE}/stavki/sport/xokkej"),
    ("basket",     "баскетбол",   f"{WINLINE_BASE}/stavki/sport/basketbol"),
    ("tennis",     "теннис",      f"{WINLINE_BASE}/stavki/sport/tennis"),
    ("volleyball", "волейбол",    f"{WINLINE_BASE}/stavki/sport/volejbol"),
    ("esports",    "киберспорт",  f"{WINLINE_BASE}/stavki/sport/kibersport"),
    ("mma",        "единоборства",f"{WINLINE_BASE}/stavki/sport/edinoborstva"),
]

PAGE_LOAD_MS  = 5000   # ждать после загрузки
SCROLL_TIMES  = 25     # сколько раз скроллить
SCROLL_PX     = 600    # пикселей за один шаг
SCROLL_WAIT   = 500    # мс между шагами

# =============================================================================
# JS-ИЗВЛЕЧЕНИЕ — выполняется в браузере
# =============================================================================

EXTRACT_JS = r"""
() => {
    const WINLINE_BASE = 'https://winline.ru';
    const results = [];
    const seenIds = new Set();

    // Все турнирные блоки
    const tournaments = document.querySelectorAll('ww-feature-block-tournament-dsk, [class*="block-tournament"]');

    tournaments.forEach(tournament => {
        // Название лиги/турнира
        let leagueName = '';
        const leagueEl = tournament.querySelector(
            '[class*="block-tournament-header__name"], [class*="tournament-name"], ' +
            '[class*="block-tournament-header__title"], [class*="champ-name"]'
        );
        if (leagueEl) {
            leagueName = (leagueEl.innerText || leagueEl.textContent || '').trim();
        }
        // Fallback: заголовок блока
        if (!leagueName) {
            const h = tournament.querySelector('h2, h3, h4');
            if (h) leagueName = (h.innerText || '').trim();
        }

        // Карточки матчей внутри блока
        const cards = tournament.querySelectorAll('[class*="card"]');
        cards.forEach(card => {
            // Ссылка на матч
            const link = card.querySelector('a[href*="/stavki/event/"]');
            if (!link) return;
            const href = link.href || (WINLINE_BASE + link.getAttribute('href'));
            const eventId = (href.match(/\/event\/(\d+)/) || [])[1];
            if (!eventId || seenIds.has(eventId)) return;
            seenIds.add(eventId);

            // Команды
            const nameEls = card.querySelectorAll('[class*="body-left__names"] [class*="name"],' +
                ' [class*="participant-name"], [class*="team-name"]');
            const teams = [];
            nameEls.forEach(el => {
                const t = (el.innerText || el.textContent || '').trim();
                if (t && t.length > 0 && t.length < 60) teams.push(t);
            });

            // Если не нашли через селекторы — берём из текста ссылки
            if (teams.length < 2) {
                const lt = (link.innerText || link.textContent || '').trim();
                const parts = lt.split('\n').map(s => s.trim()).filter(Boolean);
                parts.forEach(p => { if (teams.indexOf(p) === -1) teams.push(p); });
            }

            const team1 = teams[0] || '';
            const team2 = teams[1] || '';
            if (!team1 || !team2) return;

            // Коэффициенты — берём кнопки-коэфициенты внутри карточки
            // П1, X, П2 — первые три coefficient-button_generic3
            const mainBtns = card.querySelectorAll('[class*="coefficient-button_generic3"]');
            const p1 = mainBtns[0] ? (mainBtns[0].innerText || '').trim() : '—';
            const x  = mainBtns[1] ? (mainBtns[1].innerText || '').trim() : '—';
            const p2 = mainBtns[2] ? (mainBtns[2].innerText || '').trim() : '—';

            // Дата / время — из innerText карточки
            const cardText = (card.innerText || '').replace(/\s+/g, ' ').trim();
            // "18 фев 20:00" или "20:00"
            let dateStr = '', timeStr = '';
            const dtMatch = cardText.match(/(\d{1,2})\s+(янв|фев|мар|апр|май|июн|июл|авг|сен|окт|ноя|дек)\s+(\d{1,2}:\d{2})/i);
            if (dtMatch) {
                dateStr = dtMatch[1] + ' ' + dtMatch[2].toLowerCase();
                timeStr = dtMatch[3];
            } else {
                const tmMatch = cardText.match(/\b(\d{1,2}:\d{2})\b/);
                if (tmMatch) {
                    timeStr = tmMatch[1];
                    const now = new Date();
                    const months = ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'];
                    dateStr = now.getDate() + ' ' + months[now.getMonth()];
                }
            }

            // Название лиги из текста карточки если не нашли
            let league = leagueName;
            if (!league) {
                const m = cardText.match(/^([А-ЯA-Z][^\d]+?)\s+(?:\d|[А-ЯA-Z]{2,})/);
                if (m) league = m[1].trim().substring(0, 60);
            }

            results.push({
                eventId,
                href,
                team1,
                team2,
                league: league || 'Линия',
                dateStr,
                timeStr,
                p1, x, p2,
                cardText: cardText.substring(0, 300)
            });
        });
    });

    // Fallback: если блоки не найдены — ищем все карточки напрямую
    if (results.length === 0) {
        const allLinks = document.querySelectorAll('a[href*="/stavki/event/"]');
        allLinks.forEach(link => {
            const href = link.href || (WINLINE_BASE + link.getAttribute('href'));
            const eventId = (href.match(/\/event\/(\d+)/) || [])[1];
            if (!eventId || seenIds.has(eventId)) return;
            seenIds.add(eventId);

            const lt = (link.innerText || link.textContent || '').trim();
            const parts = lt.split('\n').map(s => s.trim()).filter(Boolean);
            const team1 = parts[0] || '';
            const team2 = parts[1] || '';
            if (!team1 || !team2) return;

            // Ищем карточку выше
            let card = link;
            for (let i = 0; i < 5; i++) {
                if (card.parentElement) card = card.parentElement;
                if ((card.className || '').toLowerCase().includes('card')) break;
            }

            const mainBtns = card.querySelectorAll('[class*="coefficient-button_generic3"]');
            const p1 = mainBtns[0] ? (mainBtns[0].innerText || '').trim() : '—';
            const x  = mainBtns[1] ? (mainBtns[1].innerText || '').trim() : '—';
            const p2 = mainBtns[2] ? (mainBtns[2].innerText || '').trim() : '—';

            const cardText = (card.innerText || '').replace(/\s+/g, ' ').trim();
            let dateStr = '', timeStr = '';
            const dtMatch = cardText.match(/(\d{1,2})\s+(янв|фев|мар|апр|май|июн|июл|авг|сен|окт|ноя|дек)\s+(\d{1,2}:\d{2})/i);
            if (dtMatch) {
                dateStr = dtMatch[1] + ' ' + dtMatch[2].toLowerCase();
                timeStr = dtMatch[3];
            } else {
                const tmMatch = cardText.match(/\b(\d{1,2}:\d{2})\b/);
                if (tmMatch) {
                    timeStr = tmMatch[1];
                    const now = new Date();
                    const months = ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'];
                    dateStr = now.getDate() + ' ' + months[now.getMonth()];
                }
            }

            results.push({ eventId, href, team1, team2, league: 'Линия', dateStr, timeStr, p1, x, p2, cardText: cardText.substring(0, 200) });
        });
    }

    return results;
}
"""


# =============================================================================
# ОБРАБОТКА СЫРЫХ ДАННЫХ
# =============================================================================

def is_valid_coef(s: str) -> bool:
    """Проверяет что строка — корректный коэффициент."""
    try:
        v = float(s.replace(',', '.'))
        return 1.01 <= v <= 50.0
    except Exception:
        return False


def fmt_coef(s: str) -> str:
    if not s or s in ('—', '-', ''):
        return '—'
    s = s.strip()
    if is_valid_coef(s):
        return s
    return '—'


def process_raw(raw: dict, sport: str) -> dict | None:
    team1 = raw.get('team1', '').strip()
    team2 = raw.get('team2', '').strip()

    # Убираем мусор из имён команд
    DATE_RX = r'\d{1,2}\s+[а-яёА-ЯЁa-zA-Z]{2,3}\s+\d{1,2}:\d{2}'
    team1 = re.sub(DATE_RX, '', team1).strip()
    team2 = re.sub(DATE_RX, '', team2).strip()
    # Убираем мусорные символы в начале/конце, но сохраняем скобки ()
    team1 = re.sub(r'^[^\w(]+|[^\w)]+$', '', team1).strip()
    team2 = re.sub(r'^[^\w(]+|[^\w)]+$', '', team2).strip()

    if not team1 or not team2 or team1 == team2:
        return None
    if len(team1) < 2 or len(team2) < 2:
        return None

    league = raw.get('league', '').strip() or f"{sport.capitalize()}"
    # Убираем лишнее из названия лиги
    league = re.sub(r'\s+', ' ', league).strip()
    if len(league) < 2:
        league = f"{sport.capitalize()}"

    return {
        "sport":     sport,
        "league":    league,
        "id":        raw.get('eventId', ''),
        "date":      raw.get('dateStr', ''),
        "time":      raw.get('timeStr', ''),
        "team1":     team1,
        "team2":     team2,
        "match_url": raw.get('href', ''),
        "p1":        fmt_coef(raw.get('p1', '')),
        "x":         fmt_coef(raw.get('x', '')),
        "p2":        fmt_coef(raw.get('p2', '')),
        "p1x":       "—",
        "p12":       "—",
        "px2":       "—",
        "source":    "winline",
    }


# =============================================================================
# ПАРСЕР СТРАНИЦЫ
# =============================================================================

def scroll_and_load(page: Page) -> None:
    """Медленный скролл для подгрузки виртуального списка."""
    for _ in range(SCROLL_TIMES):
        page.evaluate(f"window.scrollBy(0, {SCROLL_PX})")
        page.wait_for_timeout(SCROLL_WAIT)
    # Скролл вверх и ещё раз вниз — иногда помогает
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(500)
    for _ in range(SCROLL_TIMES // 2):
        page.evaluate(f"window.scrollBy(0, {SCROLL_PX * 2})")
        page.wait_for_timeout(400)


def parse_sport_page(page: Page, sport: str, url: str) -> List[dict]:
    print(f"  → {url}")
    try:
        page.goto(url, timeout=35_000, wait_until="domcontentloaded")
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

        # Блокируем рекламу и тяжёлые ресурсы
        def block_fn(route):
            url = route.request.url
            if any(x in url for x in [
                'adriver', 'yandex.ru/mc', 'mail.ru/counter',
                'beeline.ru', 'adfox', 'doubleclick', 'sbermarketing',
                'stbid.ru', 'bidvol', 'adspend', 'rtb.',
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
# СОХРАНЕНИЕ
# =============================================================================

def save_matches(matches: List[dict]) -> None:
    # Дедупликация
    seen = {}
    for m in matches:
        k = m.get("id", "")
        if k and k not in seen:
            seen[k] = m
    unique = list(seen.values())

    # Сортировка
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

    # Убираем матчи без коэффициентов И без дат (бесполезные)
    valid = [m for m in unique if not (
        m.get('p1') == '—' and m.get('x') == '—' and m.get('p2') == '—'
        and not m.get('date')
    )]

    # Добавляем source к каждому матчу
    for m in valid:
        if 'source' not in m:
            m['source'] = 'winline'

    data = {
        "last_update": datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        "source": "winline.ru",
        "total": len(valid),
        "matches": valid,
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
    print("PRIZMBET — Парсер реальных матчей Winline")
    print("Источник: winline.ru/stavki")
    print("=" * 60)

    matches = run_parser()

    if not matches:
        print("\nERROR: матчи не найдены")
        sys.exit(1)

    save_matches(matches)

    # Статистика
    from collections import Counter
    sports = Counter(m['sport'] for m in matches)
    print("\nПо видам спорта:")
    for s, c in sorted(sports.items(), key=lambda x: -x[1]):
        print(f"  {s}: {c}")

    print("\n" + "=" * 60)
    print("ГОТОВО")


if __name__ == "__main__":
    main()
