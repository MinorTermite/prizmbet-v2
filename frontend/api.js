// ===== КОНФИГУРАЦИЯ =====
const AUTO_REFRESH_MS = 5 * 60 * 1000;
const LS_CACHE_KEY = 'prizmbet_matches_cache';
const LS_FULL_KEY  = 'prizmbet_matches_full_cache';

// ===== CACHE HELPERS =====
function _getLS(key) {
    try { const r = localStorage.getItem(key); return r ? JSON.parse(r) : null; }
    catch { return null; }
}
function _setLS(key, data) {
    try { localStorage.setItem(key, JSON.stringify(data)); } catch { }
}

function fmtTime(ts) {
    if (!ts) return '—';
    const d = new Date(ts);
    if (isNaN(d.getTime())) return ts;
    return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function showStatus(ts, extra) {
    const el = document.getElementById('lastUpdate');
    if (!el) return;
    el.innerHTML = `Обновлено: ${fmtTime(ts)}${extra || ''}`;
}

function showShimmer() {
    const content = document.getElementById('content');
    if (!content) return;
    let html = '';
    for (let i = 0; i < 6; i++) html += '<div class="skeleton-card shimmer"></div>';
    content.innerHTML = html;
}

// ===== CACHE-BUST: round to 10-minute windows (CDN/browser cache friendly) =====
function cacheBust() { return Math.floor(Date.now() / 600000); }

// ===== FETCH HELPER =====
async function _fetchJson(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
}

// ===== MAIN LOAD =====
// mode: 'fast' (default) = matches-today.json  |  'full' = matches.json
async function loadData(mode) {
    const isFull = mode === 'full';
    const cacheKey = isFull ? LS_FULL_KEY : LS_CACHE_KEY;

    // 1. Show cached data instantly
    const cached = _getLS(cacheKey) || _getLS(LS_CACHE_KEY);
    if (cached?.matches?.length) {
        if (typeof renderMatches === 'function') renderMatches(cached.matches);
        showStatus(cached.last_update, ' <span style="font-size:.75em;opacity:.6">(кэш)</span>');
    } else {
        showShimmer();
    }

    // 2. Fetch JSON
    const file = isFull ? 'matches.json' : 'matches-today.json';
    let data = null;
    try {
        data = await _fetchJson(`${file}?v=${cacheBust()}`);
    } catch (e) { console.warn(`[api] ${file} fetch:`, e.message); }

    if (data?.matches?.length) {
        _setLS(cacheKey, data);
        if (typeof renderMatches === 'function') renderMatches(data.matches);
        if (data.total) {
            const el = document.getElementById('totalMatches');
            if (el) el.textContent = data.total;
        }
        const label = isFull ? ' <span style="font-size:.75em;opacity:.6">(все)</span>'
                              : ' <span style="font-size:.75em;opacity:.6">(сегодня)</span>';
        showStatus(data.last_update, label);
    }
}

// ===== AUTO-REFRESH =====
setInterval(() => { if (document.visibilityState === 'visible') loadData(); }, AUTO_REFRESH_MS);
