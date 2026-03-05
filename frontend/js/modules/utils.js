/**
 * PrizmBet v2 - Utils Module
 */

export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

export function parseMatchDateTime(match) {
    if (!match.match_time) return new Date(0);
    return new Date(match.match_time);
}

export function isMatchLive(match) {
    const start = parseMatchDateTime(match);
    const now = new Date();
    const diffHours = (now - start) / (1000 * 60 * 60);
    return diffHours >= 0 && diffHours < 2;
}

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

// Global UI helpers
export function initScrollProgress() {
    window.addEventListener('scroll', () => {
        const h = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        const bar = document.getElementById('scrollProgress');
        if (h > 0 && bar) {
            bar.style.width = ((document.documentElement.scrollTop / h) * 100) + '%';
        }
    });
}

export function initTabsHint() {
    const tabs = document.getElementById('tabsRow');
    const wrap = document.getElementById('tabsWrap');
    if (!tabs || !wrap) return;

    tabs.addEventListener('scroll', () => {
        const atEnd = tabs.scrollLeft + tabs.clientWidth >= tabs.scrollWidth - 8;
        wrap.classList.toggle('scrolled-end', atEnd);
    }, { passive: true });
}

export function shareMatch(id, showToast) {
    const url = `${window.location.origin}${window.location.pathname}#match-${id}`;
    navigator.clipboard.writeText(url).then(() => {
        if (showToast) showToast('Ссылка на матч скопирована!');
        const el = document.getElementById('match-' + id);
        if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            el.classList.add('highlight-pulse');
            setTimeout(() => el.classList.remove('highlight-pulse'), 1500);
        }
    });
}
