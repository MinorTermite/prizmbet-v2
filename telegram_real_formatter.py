#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRIZMBET - Генератор сообщений для Telegram (РЕАЛЬНЫЕ МАТЧИ)
Формат: Нэшвилл vs Детройт - П1 - 3.44 (17 фев 00:44)
"""

import json
import sys
import io

# Исправление кодировки для Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

EMOJI = {
    'football': '⚽',
    'hockey': '🏒',
    'basket': '🏀',
    'tennis': '🎾',
    'esports': '🎮',
    'volleyball': '🏐',
    'mma': '🥊'
}

def generate_message(count=20):
    """Генерирует сообщение с реальными матчами и коэффициентами"""
    d = json.load(open('matches.json', encoding='utf-8'))
    matches = d['matches'][:count]
    
    lines = []
    lines.append('🔥 ГОРЯЧИЕ МАТЧИ — РЕАЛЬНАЯ ЛИНИЯ 🔥\n')
    
    for i, m in enumerate(matches, 1):
        sport = m.get('sport', 'football')
        emoji = EMOJI.get(sport, '📌')
        t1 = m['team1']
        t2 = m['team2']
        p1 = m.get('p1', '0.00')
        date = m['date']
        time = m['time']
        
        # Формат: Команда1 vs Команда2 - П1 - 3.44 (17 фев 00:44)
        line = f"{i}. {emoji} {t1} vs {t2} - П1 - {p1} ({date} {time})"
        lines.append(line)
    
    return '\n'.join(lines)

if __name__ == "__main__":
    msg = generate_message(20)
    print(msg)
    
    # Сохраняем в файл
    with open('telegram_real_message.txt', 'w', encoding='utf-8') as f:
        f.write(msg)
    print('\n\n[OK] Sohraneno v telegram_real_message.txt')
