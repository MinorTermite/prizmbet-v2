// PrizmBet v2 - Main Application Module
import * as ui from './modules/ui.js';
import * as fav from './modules/favorites.js';
import * as notif from './modules/notifications.js';
import * as filters from './modules/filters.js';
import * as betSlip from './modules/bet_slip.js';
import * as history from './modules/history.js';

// Global state
let currentSportsFilter = 'football';
let currentLeagueFilter = 'all';
let currentSort = 'none';
let currentBet = null;

// Attach modules to window for legacy HTML handlers (onclick, etc.)
Object.assign(window, {
    ...ui, ...fav, ...notif, ...filters, ...betSlip, ...history,
    toggleFavorite: (id) => {
        fav.toggleFavorite(id, window.__ALL_MATCHES__);
        renderMatches(window.__ALL_MATCHES__);
        ui.showToast('Изменено в избранном');
    },
    requestNotificationPermission: async () => {
        const granted = await notif.requestNotificationPermission();
        if (granted) ui.showToast('Уведомления включены!');
        updateNotifBell();
    },
    openBetSlip: (id, teams, betType, coef, datetime, league) => {
        currentBet = { id, teams, betType, coef, datetime, league };
        betSlip.openBetSlip(currentBet, betType, coef);
    },
    copyBetSlipData: () => {
        betSlip.copyBetSlipData(currentBet);
    },
    onSearchInput: () => renderMatches(window.__ALL_MATCHES__ || []),
    refreshData: () => window.refreshData() // from api.js
});

/**
 * Main Orchestrator
 */
function renderMatches(allMatches) {
    if (!allMatches) return;
    window.__ALL_MATCHES__ = allMatches;
    
    // Check for finished matches in favorites
    notif.checkFinishedFavorites(allMatches);

    const state = {
        sport: currentSportsFilter,
        league: currentLeagueFilter,
        search: document.getElementById('searchInput')?.value,
        popularOnly: document.getElementById('popularOnly')?.checked
    };

    let filtered = filters.filterMatches(allMatches, state);
    filtered = filters.sortMatches(filtered, currentSort);
    
    // Update UI components
    filters.buildLeagueFilter(allMatches);
    updateStats(filtered);
    renderToDom(filtered);
}

function updateStats(matches) {
    document.getElementById('totalMatches').textContent = matches.length;
    document.getElementById('totalLeagues').textContent = new Set(matches.map(m => m.league)).size;
}

function renderToDom(matches) {
    const container = document.getElementById('content');
    if (!container) return;
    
    if (matches.length === 0) {
        container.innerHTML = '<div class="section"><p style="text-align:center; color:var(--text-tertiary);">Матчи не найдены</p></div>';
        return;
    }

    const favs = fav.getFavorites();
    const html = matches.map(m => createMatchCard(m, favs)).join('');
    container.innerHTML = `<div class="section">${html}</div>`;
}

function createMatchCard(m, favs) {
    const isFav = favs.includes(m.id);
    const t1 = ui.escapeHtml(m.team1 || '');
    const t2 = ui.escapeHtml(m.team2 || '');
    const countdown = ui.getCountdownText(m);
    
    return `
        <div class="match-card ${isFav ? 'favorited' : ''}" id="match-${m.id}">
            <div class="match-header">
                <span class="match-id">#${m.id.slice(-6)}</span>
                <div class="match-actions">
                    <button onclick="shareMatch('${m.id}')">🔗</button>
                    <button class="${isFav ? 'active' : ''}" onclick="toggleFavorite('${m.id}')">★</button>
                </div>
            </div>
            <div class="match-time">${m.date || ''} ${m.time || ''} ${countdown ? `<span class="countdown">${countdown}</span>` : ''}</div>
            <div class="match-teams">${t1} vs ${t2}</div>
            <div class="odds-container">
                <button onclick="openBetSlip('${m.id}', '${t1} vs ${t2}', 'П1', '${m.p1}', '${m.date} ${m.time}', '${m.league}')">П1: ${m.p1 || '—'}</button>
                <button onclick="openBetSlip('${m.id}', '${t1} vs ${t2}', 'X', '${m.x}', '${m.date} ${m.time}', '${m.league}')">X: ${m.x || '—'}</button>
                <button onclick="openBetSlip('${m.id}', '${t1} vs ${t2}', 'П2', '${m.p2}', '${m.date} ${m.time}', '${m.league}')">П2: ${m.p2 || '—'}</button>
            </div>
        </div>
    `;
}

function updateNotifBell() {
    const btn = document.getElementById('notifBtn');
    if (!btn) return;
    if (Notification.permission === 'granted') {
        btn.textContent = '🔔';
        btn.style.opacity = '1';
    } else {
        btn.textContent = '🔕';
        btn.style.opacity = '0.5';
    }
}

// Event Listeners for Filter orchestration
function wireEvents() {
    document.querySelectorAll('.tab').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentSportsFilter = btn.dataset.sport;
            renderMatches(window.__ALL_MATCHES__);
        });
    });

    document.getElementById('gameFilter')?.addEventListener('change', e => {
        currentLeagueFilter = e.target.value;
        renderMatches(window.__ALL_MATCHES__);
    });

    document.querySelectorAll('.sort-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentSort = btn.dataset.sort;
            renderMatches(window.__ALL_MATCHES__);
        });
    });

    window.addEventListener('betPlaced', e => {
        history.saveBetToHistory(e.detail);
        ui.showToast('✅ Ставка сохранена в историю');
    });
}

// Initialization
window.addEventListener('load', () => {
    ui.initScrollProgress();
    ui.initTabsHint();
    wireEvents();
    updateNotifBell();
    
    // Initial data load (loadData comes from api.js)
    if (window.loadData) {
        window.loadData().then(() => {
            if (window.__ALL_MATCHES__) renderMatches(window.__ALL_MATCHES__);
        });
    }
});

// Export renderMatches for api.js to call
window.renderMatches = renderMatches;
