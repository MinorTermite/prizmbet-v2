// ===== КОНФИГУРАЦИЯ =====
const AUTO_REFRESH_MS = 5 * 60 * 1000;
const DATA_STALE_HOURS = 48;
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

function isDataStale(ts) {
    if (!ts) return true;
    const d = new Date(ts);
    return isNaN(d.getTime()) || (Date.now() - d.getTime()) > DATA_STALE_HOURS * 3600000;
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
async function loadData() {
    // 1. Show today-only cache instantly (if available & fresh)
    const cached = _getLS(LS_CACHE_KEY);
    if (cached?.matches?.length) {
        if (typeof renderMatches === 'function') renderMatches(cached.matches);
        showStatus(cached.last_update, ' <span style="font-size:.75em;opacity:.6">(кэш)</span>');
    } else {
        showShimmer();
    }

    // 2. Fetch matches-today.json (today + tomorrow only, fast)
    let todayData = null;
    try {
        todayData = await _fetchJson(`matches-today.json?v=${cacheBust()}`);
    } catch (e) { console.warn('[api] today fetch:', e.message); }

    if (todayData?.matches?.length) {
        _setLS(LS_CACHE_KEY, todayData);
        if (typeof renderMatches === 'function') renderMatches(todayData.matches);
        // Show "total" from full dataset (stored in today_doc) if available
        if (todayData.total) {
            const el = document.getElementById('totalMatches');
            if (el) el.textContent = todayData.total;
        }
        showStatus(todayData.last_update, ' <span style="font-size:.75em;opacity:.6">(сегодня)</span>');
    }

    // 3. Fetch full matches.json in background (all dates)
    _loadFullInBackground(todayData?.last_update);
}

function _loadFullInBackground(knownTs) {
    // Delay slightly so today's matches render first
    setTimeout(async () => {
        try {
            // If we have a fresh full cache, use it and skip network
            const fullCached = _getLS(LS_FULL_KEY);
            if (fullCached?.matches?.length && !isDataStale(fullCached.last_update)) {
                // Only update if it has more matches than what's shown
                const shownCount = _getLS(LS_CACHE_KEY)?.matches?.length || 0;
                if (fullCached.matches.length > shownCount) {
                    _setLS(LS_CACHE_KEY, fullCached);
                    if (typeof renderMatches === 'function') renderMatches(fullCached.matches);
                    showStatus(fullCached.last_update);
                }
            }

            const fullData = await _fetchJson(`matches.json?v=${cacheBust()}`);
            if (!fullData?.matches?.length) return;

            // Skip if same version as today data
            if (knownTs && fullData.last_update === knownTs && fullData.total === fullData.matches.length) {
                // today.json already had all matches (small dataset case)
                _setLS(LS_FULL_KEY, fullData);
                return;
            }

            _setLS(LS_FULL_KEY, fullData);
            _setLS(LS_CACHE_KEY, fullData);
            if (typeof renderMatches === 'function') renderMatches(fullData.matches);
            showStatus(fullData.last_update);
        } catch (e) { console.warn('[api] full fetch:', e.message); }
    }, 400);
}

// ===== REFRESH (manual / auto) =====
async function refreshData() {
    const lastUpdate = document.getElementById('lastUpdate');
    if (lastUpdate) lastUpdate.innerHTML = '<span class="loading"></span> Обновление...';

    try {
        // Bust cache with timestamp to force re-fetch
        const data = await _fetchJson('matches.json?t=' + Date.now());
        if (data?.matches?.length) {
            _setLS(LS_CACHE_KEY, data);
            _setLS(LS_FULL_KEY, data);
            if (typeof renderMatches === 'function') renderMatches(data.matches);
            showStatus(data.last_update);
            if (typeof showToast === 'function') showToast('Линия обновлена!');
            return;
        }
    } catch (e) { console.warn('[api] refresh fail:', e.message); }

    await loadData();
    if (typeof showToast === 'function') showToast('Загружены кэшированные данные');
}

// ===== AUTO-REFRESH =====
setInterval(() => { if (document.visibilityState === 'visible') loadData(); }, AUTO_REFRESH_MS);
