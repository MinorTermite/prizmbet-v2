// UI Utilities for PrizmBet

/**
 * Parses match date and time for sorting/display
 */
export function parseMatchDateTime(match) {
    if (!match.match_time) return new Date(0);
    return new Date(match.match_time);
}

/**
 * Checks if a match is currently live (started < 2 hours ago)
 */
export function isMatchLive(match) {
    const start = parseMatchDateTime(match);
    const now = new Date();
    const diffHours = (now - start) / (1000 * 60 * 60);
    return diffHours >= 0 && diffHours < 2;
}

/**
 * Returns countdown text for match start
 */
export function getCountdownText(match) {
    const start = parseMatchDateTime(match);
    const now = new Date();
    const diff = start - now;
    if (diff <= 0) return isMatchLive(match) ? "LIVE" : "Завершен";
    
    const minutes = Math.floor(diff / 60000);
    if (minutes < 60) return `${minutes} м`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} ч`;
    return `${Math.floor(hours / 24)} д`;
}

/**
 * Shows a toast notification
 */
export function showToast(msg) {
    const t = document.getElementById('betToast');
    const m = document.getElementById('betToastMessage');
    if (t && m) {
        m.textContent = msg;
        t.classList.add('show');
        setTimeout(() => t.classList.remove('show'), 3500);
    }
}

/**
 * Initializes scroll progress bar
 */
export function initScrollProgress() {
    window.addEventListener('scroll', () => {
        const h = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        const bar = document.getElementById('scrollProgress');
        if (h > 0 && bar) {
            bar.style.width = ((document.documentElement.scrollTop / h) * 100) + '%';
        }
    });
}

/**
 * Initializes mobile tabs swipe hint
 */
export function initTabsHint() {
    const tabs = document.getElementById('tabsRow');
    const wrap = document.getElementById('tabsWrap');
    if (!tabs || !wrap) return;

    tabs.addEventListener('scroll', () => {
        const atEnd = tabs.scrollLeft + tabs.clientWidth >= tabs.scrollWidth - 8;
        wrap.classList.toggle('scrolled-end', atEnd);
    }, { passive: true });
}

export function openImage(src) { window.open(src, '_blank'); }

export function shareMatch(id) {
    const url = `${window.location.origin}${window.location.pathname}#match-${id}`;
    navigator.clipboard.writeText(url).then(() => {
        showToast('Ссылка на матч скопирована!');
        const el = document.getElementById('match-' + id);
        if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            el.classList.add('highlight-pulse');
            setTimeout(() => el.classList.remove('highlight-pulse'), 1500);
        }
    });
}
