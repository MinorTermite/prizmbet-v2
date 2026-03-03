# -*- coding: utf-8 -*-
"""
Score Enricher – обогащает frontend/matches.json реальными финальными счетами.

Источник: API-Football (v3.football.api-sports.io).
Использует существующий API_FOOTBALL_KEY из .env.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

try:
    import aiohttp
except ImportError:
    print("[score_enricher] Установите aiohttp: pip install aiohttp")
    sys.exit(1)

_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_repo_root, ".env"))
except ImportError:
    pass

API_KEY = os.getenv("API_FOOTBALL_KEY", "")
BASE_URL = "https://v3.football.api-sports.io"
MATCHES_JSON = os.path.join(_repo_root, "frontend", "matches.json")

HEADERS = {
    "x-apisports-key": API_KEY,
}


def _normalize(name: str) -> str:
    """Убирает лишние символы для сравнения."""
    if not name: return ""
    return name.lower().replace("-", " ").replace("fc", "").replace("fk", "").replace("jk", "").strip()


def _teams_match(our_t1: str, our_t2: str, api_t1: str, api_t2: str) -> bool:
    """Проверяет совпадение пары команд (нечёткий поиск)."""
    our1 = _normalize(our_t1)
    our2 = _normalize(our_t2)
    api1 = _normalize(api_t1)
    api2 = _normalize(api_t2)
    
    # Прямое или обратное совпадение (если вдруг команды в другом порядке)
    def match_pair(a1, a2, b1, b2):
        # Проверяем вхождение первого слова (часто это имя клуба)
        w1_a = a1.split()[0] if a1.split() else "???"
        w2_a = a2.split()[0] if a2.split() else "???"
        w1_b = b1.split()[0] if b1.split() else "???"
        w2_b = b2.split()[0] if b2.split() else "???"
        
        match1 = (w1_a in b1 or w1_b in a1)
        match2 = (w2_a in b2 or w2_b in a2)
        return match1 and match2

    return match_pair(our1, our2, api1, api2) or match_pair(our1, our2, api2, api1)


def _parse_match_date(match_json_item: Dict) -> Optional[datetime]:
    """Парсит поля date и time матча из matches.json в datetime."""
    date_str = (match_json_item.get("date") or "").strip()
    time_str = (match_json_item.get("time") or "").strip()
    if not date_str: return None
    try:
        MONTHS = {
            "янв": 1, "фев": 2, "мар": 3, "апр": 4, "май": 5, "июн": 6,
            "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12,
        }
        parts = date_str.split()
        day = int(parts[0])
        month = MONTHS.get(parts[1].lower(), 0)
        if not month: return None
        year = datetime.now(timezone.utc).year
        hour, minute = (int(x) for x in time_str.split(":")) if ":" in time_str else (0, 0)
        return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
    except Exception:
        return None


async def _fetch_fixtures(session: aiohttp.ClientSession, date_str: str) -> List[Dict]:
    """Загружает ВСЕ матчи за конкретную дату из API-Football."""
    url = f"{BASE_URL}/fixtures"
    params = {"date": date_str}
    try:
        async with session.get(url, headers=HEADERS, params=params, timeout=20) as r:
            if r.status == 200:
                data = await r.json()
                return data.get("response", [])
            print(f"[score_enricher] API-Football {r.status} for {date_str}")
    except Exception as e:
        print(f"[score_enricher] Ошибка запроса на {date_str}: {e}")
    return []


async def main():
    if not API_KEY:
        print("[score_enricher] API_FOOTBALL_KEY не найден — пропускаем")
        return

    if not os.path.exists(MATCHES_JSON):
        print(f"[score_enricher] {MATCHES_JSON} не найден")
        return

    with open(MATCHES_JSON, encoding="utf-8") as f:
        payload = json.load(f)

    our_matches = payload.get("matches", [])
    if not our_matches:
        return

    print(f"[score_enricher] Обогащаем {len(our_matches)} матчей...")

    # Собираем уникальные даты из нашего файла
    target_dates = set()
    for m in our_matches:
        dt = _parse_match_date(m)
        if dt:
            target_dates.add(dt.strftime("%Y-%m-%d"))
    
    # Также добавим вчерашнюю дату на случай если матч только что кончился
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    target_dates.add(yesterday)
    target_dates.add(datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    all_api_fixtures = []
    async with aiohttp.ClientSession() as session:
        tasks = [_fetch_fixtures(session, ds) for ds in target_dates]
        results = await asyncio.gather(*tasks)
        for res in results:
            all_api_fixtures.extend(res)

    print(f"[score_enricher] Получено {len(all_api_fixtures)} матчей из API")

    # Строим карту счетов (учитываем только завершенные матчи)
    api_map = []
    for f in all_api_fixtures:
        status = f.get("fixture", {}).get("status", {}).get("short", "")
        if status not in ("FT", "AET", "PEN"):
            continue
        
        goals = f.get("goals", {})
        h_g = goals.get("home")
        a_g = goals.get("away")
        if h_g is None or a_g is None:
            continue
        
        teams = f.get("teams", {})
        home = teams.get("home", {}).get("name", "")
        away = teams.get("away", {}).get("name", "")
        fdate = f.get("fixture", {}).get("date", "")
        try:
            fdt = datetime.fromisoformat(fdate.replace("Z", "+00:00"))
        except:
            continue
            
        api_map.append({
            "t1": home,
            "t2": away,
            "score": f"{h_g}:{a_g}",
            "dt": fdt
        })

    updated = 0
    for m in our_matches:
        if m.get("score"): continue  # Уже есть
        if (m.get("sport") or "football") != "football": continue # Только футбол пока
        
        t1 = m.get("team1", "")
        t2 = m.get("team2", "")
        dt = _parse_match_date(m)
        
        for candidate in api_map:
            # Сверяем по дате ±24 часа
            if dt:
                if abs((candidate["dt"] - dt).total_seconds()) > 86400:
                    continue
            
            if _teams_match(t1, t2, candidate["t1"], candidate["t2"]):
                m["score"] = candidate["score"]
                updated += 1
                break

    print(f"[score_enricher] Успешно добавлено {updated} счётов")

    with open(MATCHES_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
