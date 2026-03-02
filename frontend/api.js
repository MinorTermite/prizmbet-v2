// ===== КОНФИГУРАЦИЯ =====
const AUTO_REFRESH_MS = 5 * 60 * 1000;
const DATA_STALE_HOURS = 48;
const SITE_BASE = 'https://minortermite.github.io/betprizm';
const NETLIFY_FN_URL = SITE_BASE + '/matches.json';
const LS_CACHE_KEY = 'prizmbet_matches_cache';

// ===== DATA LOADING & CACHING =====
function getCachedMatches() {
    try {
        const raw = localStorage.getItem(LS_CACHE_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch { return null; }
}

function setCachedMatches(data) {
    try { localStorage.setItem(LS_CACHE_KEY, JSON.stringify(data)); } catch { }
}

function isDataStale(ts) {
    if (!ts) return true;
    const d = new Date(ts);
    return isNaN(d.getTime()) || (Date.now() - d.getTime()) > DATA_STALE_HOURS * 3600000;
}

function fmtTime(ts) {
    if (!ts) return '—';
    const d = new Date(ts);
    return isNaN(d.getTime()) ? ts : d.toLocaleString('ru-RU');
}

function showStatus(ts, src) {
    const el = document.getElementById('lastUpdate');
    if (!el) return;
    const stale = isDataStale(ts);
    el.innerHTML = `Обновлено: ${fmtTime(ts)}${src === 'live' ? ' (live)' : ''}`;
}

async function loadData() {
    // 1. Сразу показываем кэш из localStorage (если есть) — мгновенно
    const cached = getCachedMatches();
    if (cached?.matches?.length) {
        if (typeof renderMatches === 'function') renderMatches(cached.matches);
        showStatus(cached.last_update, 'cache');
    }

    // Округляем до 10-минутного интервала — CDN и браузер могут кэшировать ответ
    const cacheBust = Math.floor(Date.now() / 600000);

    let data = null, source = 'static';
    // 2. Пробуем статичный matches.json (основной источник на GitHub Pages)
    try {
        const r = await fetch('matches.json?v=' + cacheBust);
        if (r.ok) data = await r.json();
    } catch (e) { console.warn('static fail:', e.message); }
    // 3. Fallback — пробуем абсолютный URL (GitHub Pages)
    if (!data?.matches?.length) {
        try {
            const r = await fetch(NETLIFY_FN_URL + '?v=' + cacheBust);
            if (r.ok) {
                const live = await r.json();
                if (live?.matches?.length) { data = live; source = 'live'; }
            }
        } catch (e) { console.warn('fallback fail:', e.message); }
    }

    if (data?.matches?.length) {
        setCachedMatches(data); // сохраняем в кэш
        if (typeof renderMatches === 'function') renderMatches(data.matches);
        showStatus(data.last_update, source);
    } else if (!cached?.matches?.length) {
        const content = document.getElementById('content');
        if (content) content.innerHTML = '<div class="section"><p style="text-align:center;color:var(--text-secondary);">Ошибка загрузки. Обновите страницу.</p></div>';
        const lastUpdate = document.getElementById('lastUpdate');
        if (lastUpdate) lastUpdate.textContent = 'Ошибка загрузки';
    }
}

async function refreshData() {
    const lastUpdate = document.getElementById('lastUpdate');
    if (lastUpdate) lastUpdate.innerHTML = '<span class="loading"></span> Обновление...';

    let data = null;
    try {
        const r = await fetch('matches.json?t=' + Date.now());
        if (r.ok) data = await r.json();
    } catch (e) { }

    if (data?.matches?.length) {
        setCachedMatches(data);
        if (typeof renderMatches === 'function') renderMatches(data.matches);
        showStatus(data.last_update, 'live');
        if (typeof showToast === 'function') showToast('Линия обновлена!');
    } else {
        await loadData();
        if (typeof showToast === 'function') showToast('Загружены кэшированные данные');
    }
}
