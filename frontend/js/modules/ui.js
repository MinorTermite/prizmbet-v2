/**
 * PrizmBet v2 - UI Module
 */
import { escapeHtml, getCountdownText } from './utils.js';
import { getFavorites } from './storage.js';
import { getMatchGame } from './filters.js';

export function updateStats(matches) {
    const totalMatches = document.getElementById('totalMatches');
    const totalLeagues = document.getElementById('totalLeagues');
    if (totalMatches) totalMatches.textContent = matches.length;
    if (totalLeagues) totalLeagues.textContent = new Set(matches.map(m => m.league)).size;
}

export function buildGameFilter(matches) {
    const sel = document.getElementById('gameFilter');
    if (!sel) return;
    const set = new Set();
    matches.forEach(m => set.add(getMatchGame(m)));
    const leagues = Array.from(set).sort((a, b) => a.localeCompare(b, 'ru'));
    const prev = sel.value || 'all';
    sel.innerHTML = '<option value="all">Все лиги</option>' +
        leagues.map(g => `<option value="${g}">${g}</option>`).join('');
    if (leagues.includes(prev)) sel.value = prev;
}

export function createMatchCard(m, favs) {
    const isFav = favs.includes(m.id);
    const t1 = escapeHtml(m.team1 || m.home_team || '');
    const t2 = escapeHtml(m.team2 || m.away_team || '');
    const countdown = getCountdownText(m);
    
    // Normalize p1/x/p2 for card display
    const p1 = m.p1 || m.odds_home || '—';
    const x = m.x || m.odds_draw || '—';
    const p2 = m.p2 || m.odds_away || '—';

    return `
        <div class="match-card ${isFav ? 'favorited' : ''}" id="match-${m.id}">
            <div class="match-header">
                <span class="match-id">#${m.id.slice(-6)}</span>
                <div class="match-actions">
                    <button onclick="shareMatch('${m.id}')">🔗</button>
                    <button class="${isFav ? 'active' : ''}" onclick="toggleFavorite('${m.id}')">★</button>
                </div>
            </div>
            <div class="match-time">${m.match_time ? new Date(m.match_time).toLocaleString('ru-RU', {day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit'}) : ''} ${countdown ? `<span class="countdown">${countdown}</span>` : ''}</div>
            <div class="match-teams">${t1} vs ${t2}</div>
            <div class="odds-container">
                <button onclick="openBetSlip('${m.id}', '${t1} vs ${t2}', 'П1', '${p1}', '${m.match_time}', '${m.league}')">П1: ${p1}</button>
                <button onclick="openBetSlip('${m.id}', '${t1} vs ${t2}', 'X', '${x}', '${m.match_time}', '${m.league}')">X: ${x}</button>
                <button onclick="openBetSlip('${m.id}', '${t1} vs ${t2}', 'П2', '${p2}', '${m.match_time}', '${m.league}')">П2: ${p2}</button>
            </div>
        </div>
    `;
}

export function renderMatches(matches) {
    const container = document.getElementById('content');
    if (!container) return;
    
    if (matches.length === 0) {
        container.innerHTML = '<div class="section"><p style="text-align:center; color:var(--text-tertiary);">Матчи не найдены</p></div>';
        return;
    }

    const favs = getFavorites();
    const html = matches.map(m => createMatchCard(m, favs)).join('');
    container.innerHTML = `<div class="section">${html}</div>`;
}

export function patchCardOdds(id, odds) {
    const card = document.getElementById(`match-${id}`);
    if (!card) return;
    // Implementation for dynamic updates if needed
}
