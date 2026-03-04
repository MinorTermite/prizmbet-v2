// ===== PWA Service Worker Registration =====
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('sw.js')
                    .then(reg => console.log('SW registered:', reg.scope))
                    .catch(err => console.log('SW registration failed:', err));
            });
        }

        // Конфигурация и функции кэширования/API (loadData, refreshData)
        // теперь находятся в отдельном файле api.js для соответствия принципу DRY.

        // ===== LocalStorage для избранного =====
        function getFavorites() {
            try { const f = localStorage.getItem('prizmbet_favorites'); return f ? JSON.parse(f) : []; }
            catch { return []; }
        }
        function saveFavorites(favorites) {
            try { localStorage.setItem('prizmbet_favorites', JSON.stringify(favorites)); } catch { }
        }

        // Сохраняем детали матчей избранного (команды, лига) для уведомлений
        function getFavDetails() {
            try { const d = localStorage.getItem('prizmbet_fav_details'); return d ? JSON.parse(d) : {}; }
            catch { return {}; }
        }
        function saveFavDetails(details) {
            try { localStorage.setItem('prizmbet_fav_details', JSON.stringify(details)); } catch { }
        }

        function toggleFavorite(matchId) {
            let favorites = getFavorites();
            let details = getFavDetails();
            if (favorites.includes(matchId)) {
                favorites = favorites.filter(id => id !== matchId);
                delete details[matchId];
                showToast('Убрано из избранного');
            } else {
                favorites.push(matchId);
                // Сохраняем детали матча для будущих уведомлений
                const match = (window.__ALL_MATCHES__ || []).find(m => m.id === matchId);
                if (match) {
                    details[matchId] = { team1: match.team1, team2: match.team2, league: match.league };
                }
                showToast('⭐ Добавлено в избранное');
            }
            saveFavorites(favorites);
            saveFavDetails(details);
            if (window.__ALL_MATCHES__) renderMatches(window.__ALL_MATCHES__);
        }

        // ===== Уведомления об избранных матчах =====
        function updateNotifBell() {
            const btn = document.getElementById('notifBtn');
            if (!btn) return;
            if (!('Notification' in window)) { btn.style.opacity = '0.3'; return; }
            if (Notification.permission === 'granted') {
                btn.textContent = '🔔';
                btn.title = 'Уведомления включены';
                btn.style.opacity = '1';
            } else if (Notification.permission === 'denied') {
                btn.textContent = '🔕';
                btn.title = 'Уведомления заблокированы — разрешите в настройках браузера';
                btn.style.opacity = '0.5';
            } else {
                btn.textContent = '🔔';
                btn.title = 'Нажмите, чтобы включить уведомления';
                btn.style.opacity = '0.6';
            }
        }

        function requestNotificationPermission() {
            if (!('Notification' in window)) {
                showToast('Уведомления не поддерживаются в этом браузере');
                return;
            }
            if (Notification.permission === 'granted') {
                showToast('🔔 Уведомления уже включены!');
                return;
            }
            if (Notification.permission === 'denied') {
                // Показываем модалку с инструкцией как разблокировать
                const msg = document.createElement('div');
                msg.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;border:1px solid rgba(139,92,246,0.5);border-radius:16px;padding:24px;z-index:9999;max-width:320px;width:90%;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,0.7)';
                msg.innerHTML = `
                    <div style="font-size:2rem;margin-bottom:12px">🔕</div>
                    <div style="font-weight:700;margin-bottom:8px;color:#fff">Уведомления заблокированы</div>
                    <div style="color:#aaa;font-size:0.85rem;margin-bottom:16px;line-height:1.5">
                        Chrome: нажми 🔒 в адресной строке → <b>Уведомления</b> → <b>Разрешить</b>
                    </div>
                    <button onclick="this.closest('div[style]').remove()" style="background:rgba(139,92,246,0.3);border:1px solid rgba(139,92,246,0.5);color:#fff;padding:8px 24px;border-radius:8px;cursor:pointer;font-size:0.9rem">Понятно</button>
                `;
                document.body.appendChild(msg);
                msg.addEventListener('click', e => { if (e.target === msg) msg.remove(); });
                return;
            }
            // permission === 'default' — запрашиваем у браузера
            Notification.requestPermission().then(result => {
                updateNotifBell();
                if (result === 'granted') {
                    showToast('🔔 Уведомления включены!');
                    if (navigator.vibrate) navigator.vibrate(100);
                    // Показываем тестовое уведомление
                    new Notification('PRIZMBET', {
                        body: 'Уведомления включены! Теперь вы будете получать обновления.',
                        icon: 'prizmbet-logo.webp'
                    });
                } else {
                    showToast('Уведомления отклонены');
                }
            });
        }

        function playNotificationSound() {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const now = ctx.currentTime;
                [880, 1100].forEach((freq, i) => {
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.frequency.value = freq;
                    osc.type = 'sine';
                    gain.gain.setValueAtTime(0.35, now + i * 0.28);
                    gain.gain.exponentialRampToValueAtTime(0.01, now + i * 0.28 + 0.25);
                    osc.start(now + i * 0.28);
                    osc.stop(now + i * 0.28 + 0.25);
                });
            } catch (e) { /* silent fail */ }
        }

        function checkFinishedFavorites(allMatches) {
            const favorites = getFavorites();
            if (!favorites.length) return;
            const details = getFavDetails();
            const activeIds = new Set((allMatches || []).map(m => m.id));
            const notifiedKey = 'prizmbet_notified_v2';
            let notified = [];
            try { notified = JSON.parse(localStorage.getItem(notifiedKey) || '[]'); } catch { }

            favorites.forEach(favId => {
                if (!activeIds.has(favId) && !notified.includes(favId)) {
                    const d = details[favId] || {};
                    const team1 = d.team1 || '?';
                    const team2 = d.team2 || '?';
                    const league = d.league || '';

                    // Показываем toast всегда
                    showToast(`✅ Матч завершён: ${team1} — ${team2}`);

                    // Push-уведомление если разрешено
                    if ('Notification' in window && Notification.permission === 'granted') {
                        try {
                            const n = new Notification('✅ Матч завершён — PRIZMBET', {
                                body: `${team1} — ${team2}\n${league}`,
                                icon: '/betprizm/prizmbet-logo.webp',
                                tag: `fin-${favId}`,
                                requireInteraction: false,
                            });
                            n.onclick = () => { window.focus(); n.close(); };
                        } catch (e) { /* silent */ }
                    }

                    // Звук + вибрация
                    playNotificationSound();
                    if (navigator.vibrate) navigator.vibrate([200, 80, 200, 80, 350]);

                    notified.push(favId);
                }
            });

            try { localStorage.setItem(notifiedKey, JSON.stringify(notified)); } catch { }
        }

        // ===== Scroll progress =====
        window.addEventListener('scroll', () => {
            const h = document.documentElement.scrollHeight - document.documentElement.clientHeight;
            if (h > 0) {
                document.getElementById('scrollProgress').style.width =
                    ((document.documentElement.scrollTop / h) * 100) + '%';
            }
        });

        // ===== Tabs swipe hint =====
        (function initTabsHint() {
            const tabs = document.getElementById('tabsRow');
            const wrap = document.getElementById('tabsWrap');
            if (!tabs || !wrap) return;

            // Hide fade when scrolled to end
            tabs.addEventListener('scroll', () => {
                const atEnd = tabs.scrollLeft + tabs.clientWidth >= tabs.scrollWidth - 8;
                wrap.classList.toggle('scrolled-end', atEnd);
            }, { passive: true });

            // Swipe hint animation on first load (mobile only, once per session)
            const hintKey = 'prizm_tabs_hint_shown';
            if (!sessionStorage.getItem(hintKey)) {
                sessionStorage.setItem(hintKey, '1');
                setTimeout(() => {
                    // Scroll tabs to show there's more, then back
                    const scrollTo = (target, dur) => {
                        const start = tabs.scrollLeft;
                        const diff = target - start;
                        const t0 = performance.now();
                        const step = now => {
                            const p = Math.min((now - t0) / dur, 1);
                            const ease = p < 0.5 ? 2*p*p : -1+(4-2*p)*p;
                            tabs.scrollLeft = start + diff * ease;
                            if (p < 1) requestAnimationFrame(step);
                        };
                        requestAnimationFrame(step);
                    };
                    scrollTo(80, 500);
                    setTimeout(() => scrollTo(0, 400), 700);
                }, 800);
            }
        })();

        // ===== Filters state =====
        let currentSportFilter = 'football';
        let currentGameFilter = 'all';
        let currentSort = 'none';

        function getMatchSport(m) {
            return (m.sport || '').toLowerCase() || inferSport(m);
        }

        function inferSport(m) {
            const t = ((m.league || '') + ' ' + (m.team1 || '') + ' ' + (m.team2 || '')).toLowerCase();
            if (/настольный теннис|наст\. теннис|table tennis/.test(t)) return 'tabletennis';
            if (/dota|counter-strike|cs2|valorant|league of legends|lol|rocket league|rlcs|pubg|apex|rainbow six|overwatch/.test(t)) return 'esports';
            if (/кхл|нхл|hockey|nhl|ahl|shl|liiga|del|хоккей/.test(t)) return 'hockey';
            if (/nba|нба|баскет|euroleague|евролига|vtb|acb|bbl/.test(t)) return 'basket';
            if (/теннис|atp|wta|itf|уимблдон|ролан гаррос|tennis/.test(t)) return 'tennis';
            if (/волейбол|volleyball|cev|vnl|суперлига|plusliga|superlega/.test(t)) return 'volleyball';
            if (/ufc|bellator|mma|one championship|pfl|acb mma/.test(t)) return 'mma';
            return 'football';
        }

        function getMatchGame(m) {
            if (m.game) return String(m.game);
            const l = (m.league || '').toLowerCase();
            // Football
            if (l.includes('лига чемпионов') || l.includes('champions league') || l.startsWith('лч')) return 'ЛЧ УЕФА';
            if (l.includes('лига европы') || l.includes('europa league')) return 'ЛЕ УЕФА';
            if (l.includes('лига конференций') || l.includes('conference league')) return 'ЛК УЕФА';
            if (l.includes('премьер-лига') && l.includes('англия')) return 'Англия. Премьер-лига';
            if (l.includes('чемпионшип') && l.includes('англия')) return 'Англия. Чемпионшип';
            if (l.includes('кубок') && (l.includes('англия') || l.includes('england'))) return 'Англия. Кубок';
            if (l.includes('ла лига') || l.includes('la liga')) return 'Испания. Ла Лига';
            if (l.includes('кубок короля')) return 'Испания. Кубок Короля';
            if (l.includes('бундеслига') && !l.includes('2.')) return 'Германия. Бундеслига';
            if (l.includes('2. бундеслига')) return 'Германия. 2. Бундеслига';
            if (l.includes('серия a') || l.includes('serie a')) return 'Италия. Серия A';
            if (l.includes('серия b') || l.includes('serie b')) return 'Италия. Серия B';
            if (l.includes('лига 1') && (l.includes('франция') || l.includes('france'))) return 'Франция. Лига 1';
            if (l.includes('эредивизие')) return 'Нидерланды. Эредивизие';
            if (l.includes('примейра') || l.includes('primeira')) return 'Португалия. Примейра Лига';
            if (l.includes('суперлига') && l.includes('турция')) return 'Турция. Суперлига';
            if (l.includes('премьершип') && l.includes('шотл')) return 'Шотландия. Премьершип';
            if (l.includes('про лига') && l.includes('бельг')) return 'Бельгия. Про Лига';
            if (l.includes('премьер-лига') && l.includes('россия')) return 'Россия. Премьер-лига';
            if (l.includes('фнл')) return 'Россия. ФНЛ';
            if (l.includes('кубок') && l.includes('россия')) return 'Россия. Кубок';
            if (l.includes('серия a') && l.includes('бразилия')) return 'Бразилия. Серия A';
            if (l.includes('примера') && l.includes('аргент')) return 'Аргентина. Примера';
            if (l.includes('mls') || l.includes('сша')) return 'США. MLS';
            if (l.includes('лига mx') || l.includes('мексик')) return 'Мексика. Лига MX';
            if (l.includes('копа либертадорес')) return 'Копа Либертадорес';
            if (l.includes('саудовская арав')) return 'Саудовская Аравия';
            if (l.includes('джей-лига') || l.includes('яп')) return 'Япония. Джей-Лига';
            if (l.includes('к-лига') || l.includes('корея')) return 'Южная Корея. К-Лига';
            // Hockey
            if (l.includes('кхл')) return 'КХЛ';
            if (l.includes('нхл') || l.includes('nhl')) return 'НХЛ';
            if (l.includes('вхл')) return 'ВХЛ';
            if (l.includes('shl')) return 'Швеция. SHL';
            if (l.includes('liiga')) return 'Финляндия. Liiga';
            if (l.includes('extraliga') && l.includes('чех')) return 'Чехия. Extraliga';
            if (l.includes('del') && l.includes('герм')) return 'Германия. DEL';
            if (l.includes('экстралига') && l.includes('белар')) return 'Беларусь. Экстралига';
            // Basketball
            if (l.includes('nba') || l.includes('нба')) return 'NBA';
            if (l.includes('евролига') || l.includes('euroleague')) return 'Евролига';
            if (l.includes('втб')) return 'Единая лига ВТБ';
            if (l.includes('acb')) return 'Испания. ACB';
            if (l.includes('bsl') && l.includes('турц')) return 'Турция. BSL';
            if (l.includes('nbl') && l.includes('австрал')) return 'Австралия. NBL';
            if (l.includes('cba') && l.includes('китай')) return 'Китай. CBA';
            // Esports
            if (l.includes('dota 2')) return 'Dota 2';
            if (l.includes('counter-strike') || l.includes('cs2')) return 'CS2';
            if (l.includes('valorant')) return 'Valorant';
            if (l.includes('league of legends') || l.includes('lck') || l.includes('lpl') || l.includes('lec')) return 'League of Legends';
            if (l.includes('rocket league') || l.includes('rlcs')) return 'Rocket League';
            if (l.includes('pubg')) return 'PUBG';
            if (l.includes('apex')) return 'Apex Legends';
            // Tennis
            if (l.includes('atp') && l.includes('мадрид')) return 'ATP. Мадрид';
            if (l.includes('atp') && l.includes('рим')) return 'ATP. Рим';
            if (l.includes('atp') && l.includes('roland') || l.includes('ролан')) return 'ATP. Roland Garros';
            if (l.includes('уимблдон') || l.includes('wimbledon')) return 'Уимблдон';
            if (l.includes('us open')) return 'US Open';
            if (l.startsWith('atp')) return 'ATP Tour';
            if (l.startsWith('wta')) return 'WTA Tour';
            // Volleyball
            if (l.includes('cev')) return 'CEV. Лига чемпионов';
            if (l.includes('внл') || l.includes('vnl')) return 'Лига наций ВНЛ';
            if (l.includes('суперлига') && !l.includes('турц') && !l.includes('баск')) return 'Россия. Суперлига Волейбол';
            if (l.includes('plusliga') || l.includes('польша')) return 'Польша. PlusLiga';
            if (l.includes('superlega') || l.includes('итал')) return 'Италия. SuperLega';
            // MMA
            if (l.includes('ufc')) return 'UFC';
            if (l.includes('bellator')) return 'Bellator MMA';
            if (l.includes('one championship') || l.includes('one fc')) return 'ONE Championship';
            if (l.includes('acb mma')) return 'ACB MMA';
            if (l.includes('pfl')) return 'PFL';
            return m.league || 'Другое';
        }

        // ===== Парсинг даты и времени =====
        function parseMatchDateTime(match) {
            const now = new Date();
            const dateStr = match.date || '';
            const timeStr = match.time || '';
            const monthMap = { 'янв': 0, 'фев': 1, 'мар': 2, 'апр': 3, 'май': 4, 'июн': 5, 'июл': 6, 'авг': 7, 'сен': 8, 'окт': 9, 'ноя': 10, 'дек': 11 };
            const dateParts = dateStr.match(/(\d+)\s+(\w+)/);
            const timeParts = timeStr.match(/(\d+):(\d+)/);
            if (dateParts && timeParts) {
                const day = parseInt(dateParts[1]);
                const monthStr = dateParts[2].toLowerCase();
                const month = monthMap[monthStr] !== undefined ? monthMap[monthStr] : now.getMonth();
                const hour = parseInt(timeParts[1]);
                const minute = parseInt(timeParts[2]);
                let year = now.getFullYear();
                if (month < now.getMonth()) year++;
                return new Date(year, month, day, hour, minute);
            }
            return null;
        }

        function isMatchLive(match) {
            const matchDate = parseMatchDateTime(match);
            if (!matchDate) return false;
            const diffMs = matchDate - new Date();
            return diffMs < 0 && diffMs > -3 * 60 * 60 * 1000;
        }

        function getCountdownText(match) {
            const matchDate = parseMatchDateTime(match);
            if (!matchDate) return '';
            const diffMs = matchDate - new Date();
            if (diffMs < 0) return '';
            const diffMinutes = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMinutes / 60);
            const diffDays = Math.floor(diffHours / 24);
            if (diffDays > 0) return `через ${diffDays}д`;
            if (diffHours > 0) return `через ${diffHours}ч`;
            if (diffMinutes > 0) return `через ${diffMinutes}м`;
            return 'скоро';
        }

        function escapeHtml(text) {
            const d = document.createElement('div');
            d.textContent = text;
            return d.innerHTML;
        }

        function buildGameFilter(matches) {
            const sel = document.getElementById('gameFilter');
            if (!sel) return;
            const set = new Set();
            matches.forEach(m => set.add(getMatchGame(m)));
            const games = Array.from(set).sort((a, b) => a.localeCompare(b, 'ru'));
            const prev = sel.value || 'all';
            sel.innerHTML = '<option value="all">Все лиги</option>' +
                games.map(g => `<option value="${escapeHtml(g)}">${escapeHtml(g)}</option>`).join('');
            if (games.includes(prev)) sel.value = prev;
        }

        function isValidMatch(m) {
            const team1 = (m.team1 || '').trim();
            const team2 = (m.team2 || '').trim();
            const league = (m.league || '').toLowerCase();

            if (!team1 || !team2) return false;

            if (/^(1|x|12|x2|2|0|-)$/i.test(team2)) return false;

            if (/^\d+\.?\d*$/.test(team2)) return false;

            if (team2.length < 2) return false;

            if (/счет|серия|score/i.test(team1 + team2)) return false;

            const leagueInTeam = ['nba', 'nfl', 'nhl', 'ufc', 'wta', 'atp'].some(x =>
                team1.toLowerCase().includes(x) || team2.toLowerCase().includes(x));
            if (leagueInTeam && !/basketball|tennis|mma|hockey|esports/.test(league)) {
                if (team1.toLowerCase() === team2.toLowerCase()) return false;
            }

            return true;
        }

        function getFilterState() {
            return {
                q: (document.getElementById('searchInput')?.value || '').trim().toLowerCase(),
                pop: !!document.getElementById('popularOnly')?.checked,
                favOnly: !!document.getElementById('favoritesOnly')?.checked,
                favs: getFavorites(),
                sport: currentSportFilter,
                game: currentGameFilter,
                sort: currentSort
            };
        }

        function filterMatches(matches, filters) {
            let filtered = matches.filter(isValidMatch);
            // Убираем live-матчи: показываем только предстоящие, 
            // КРОМЕ случая просмотра результатов
            if (filters.sport !== 'results') {
                filtered = filtered.filter(m => !isMatchLive(m));
            }
            filtered = filtered.filter(m => {
                const sport = getMatchSport(m);
                const game = getMatchGame(m);
                if (filters.sport !== 'all' && filters.sport !== 'favs' && filters.sport !== 'totals' && filters.sport !== 'results' && sport !== filters.sport) return false;
                if (filters.game !== 'all' && game !== filters.game) return false;
                if (filters.pop && filters.sport !== 'totals' && filters.sport !== 'results') {
                    const combined = ((game || '') + ' ' + (m.league || '')).toLowerCase();
                    if (!/(лига чемпионов|лига европы|лига конференций|премьер-лига англия|ла лига|бундеслига|серия a|лига 1 франция|nba|нхл|кхл|евролига|атп|wta|ufc)/.test(combined)) {
                        if (/(dota|cs2|valorant)/.test(combined)) return false;
                    }
                }
                if (filters.favOnly || filters.sport === 'favs') {
                    if (!filters.favs.includes(m.id)) return false;
                }
                if (filters.sport === 'totals') {
                    const hasTotals = m.total_over && m.total_over !== '0.00' && m.total_value;
                    if (!hasTotals || parseFloat(m.total_value) !== 2.5) return false;
                }
                if (filters.sport === 'results') {
                    if (!m.score) return false;
                }
                if (filters.q) {
                    const blob = ((m.id || '') + ' ' + (m.league || '') + ' ' + (m.team1 || '') + ' ' + (m.team2 || '') + ' ' + game).toLowerCase();
                    if (!blob.includes(filters.q)) return false;
                }
                return true;
            });
            return filtered;
        }

        // Топ-лиги (приоритет - меньше число = выше приоритет)
        const LEAGUE_PRIORITY = {
            'лига чемпионов уэфа': 1, 'champions league': 1, 'лч': 1,
            'лига европы уэфа': 2, 'europa league': 2, 'ле': 2,
            'лига конференций': 3, 'conference league': 3, 'лк': 3,
            'англия. премьер-лига': 10, 'премьер-лига англия': 10,
            'испания. ла лига': 11, 'la liga': 11,
            'германия. бундеслига': 12, 'бундеслига германия': 12,
            'италия. серия a': 13, 'serie a': 13,
            'франция. лига 1': 14, 'лига 1 франция': 14,
            'россия. премьер-лига': 15,
            'нидерланды. эредивизие': 16,
            'португалия. примейра лига': 17,
            'турция. суперлига': 18,
            'бельгия. про лига': 19,
            'аргентина. примера': 20,
            'бразилия. серия a': 21,
            'сша. mls': 22, 'mls': 22,
            'кхл': 30, 'нхл': 31, 'nhl': 31,
            'nba': 40, 'нба': 40, 'евролига': 41, 'euroleague': 41,
            'dota 2': 50, 'cs2': 51, 'counter-strike': 51, 'valorant': 52, 'league of legends': 53,
            'atp': 60, 'wta': 61,
            'ufc': 70,
        };

        function getLeaguePriority(match) {
            const league = (match.league || '').toLowerCase();
            const sport = getMatchSport(match);
            let sportPriority = 0;
            if (sport === 'football') sportPriority = 0;
            else if (sport === 'hockey') sportPriority = 100;
            else if (sport === 'basketball') sportPriority = 200;
            else if (sport === 'tennis') sportPriority = 300;
            else if (sport === 'volleyball') sportPriority = 400;
            else if (sport === 'mma') sportPriority = 500;
            else if (sport === 'esports') sportPriority = 800;
            else sportPriority = 900;
            for (const [key, priority] of Object.entries(LEAGUE_PRIORITY)) {
                if (league.includes(key)) return sportPriority + priority;
            }
            return sportPriority + 999;
        }

        function sortMatches(matches, sortType) {
            const sorted = [...matches];
            if (sortType === 'time') {
                sorted.sort((a, b) => {
                    const dateA = parseMatchDateTime(a);
                    const dateB = parseMatchDateTime(b);
                    if (!dateA && !dateB) return 0;
                    if (!dateA) return 1;
                    if (!dateB) return -1;
                    return dateA - dateB;
                });
            } else if (sortType === 'odds') {
                sorted.sort((a, b) => {
                    const avgA = (parseFloat(a.p1 || 0) + parseFloat(a.p2 || 0)) / 2;
                    const avgB = (parseFloat(b.p1 || 0) + parseFloat(b.p2 || 0)) / 2;
                    return avgB - avgA;
                });
            } else if (sortType === 'league') {
                sorted.sort((a, b) => {
                    return (a.league || '').localeCompare(b.league || '', 'ru');
                });
            }
            return sorted;
        }

        function updateStats(matches) {
            document.getElementById('totalMatches').textContent = matches.length;
            document.getElementById('totalLeagues').textContent = new Set(matches.map(m => m.league)).size;
            const avg = matches.reduce((s, m) => s + ((parseFloat(m.p1) || 0) + (parseFloat(m.p2) || 0)) / 2, 0) / Math.max(matches.length, 1);
            document.getElementById('avgOdds').textContent = avg.toFixed(2);
        }

        function wireFilters() {
            document.querySelectorAll('.tab').forEach(btn => {
                btn.addEventListener('click', () => {
                    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    currentSportFilter = btn.dataset.sport || 'all';
                    if (window.__ALL_MATCHES__) renderMatches(window.__ALL_MATCHES__);
                });
            });
            document.getElementById('gameFilter')?.addEventListener('change', e => {
                currentGameFilter = e.target.value || 'all';
                if (window.__ALL_MATCHES__) renderMatches(window.__ALL_MATCHES__);
            });
            document.getElementById('searchInput')?.addEventListener('input', () => {
                if (window.__ALL_MATCHES__) renderMatches(window.__ALL_MATCHES__);
            });
            document.getElementById('popularOnly')?.addEventListener('change', () => {
                if (window.__ALL_MATCHES__) renderMatches(window.__ALL_MATCHES__);
            });
            document.getElementById('favoritesOnly')?.addEventListener('change', () => {
                if (window.__ALL_MATCHES__) renderMatches(window.__ALL_MATCHES__);
            });
            document.querySelectorAll('.sort-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    currentSort = btn.dataset.sort || 'time';
                    if (window.__ALL_MATCHES__) renderMatches(window.__ALL_MATCHES__);
                });
            });
        }

        // ── Создание DOM-карточки матча ────────────────────────────
        function createMatchCard(match, favorites) {
            const eid = match.id || '';
            const isFav = favorites.includes(match.id);
            const t1 = escapeHtml(match.team1 || '');
            const t2 = escapeHtml(match.team2 || '');
            const teams = `${t1} vs ${t2}`;
            const countdown = getCountdownText(match);
            const shortId = String(eid).replace(/^[a-z]+_/i, '').slice(-6);
            
            // Если матч завершен (есть счет и нет коэффициентов для ставок)
            // ПРИМЕЧАНИЕ: мы считаем матч завершенным, если есть score, либо если мы на вкладке результатов
            if (match.score) {
                // Парсим счет (например "2:1" -> [2, 1])
                let score1 = '-', score2 = '-';
                if (match.score.includes(':')) {
                    const parts = match.score.split(':');
                    score1 = parts[0].trim();
                    score2 = parts[1].trim();
                } else if (match.score.includes('-')) {
                    const parts = match.score.split('-');
                    score1 = parts[0].trim();
                    score2 = parts[1].trim();
                } else {
                    score1 = match.score;
                    score2 = '';
                }

                // Генерация инициалов для логотипов
                const init1 = t1.substring(0, 2).toUpperCase();
                const init2 = t2.substring(0, 2).toUpperCase();
                
                const card = document.createElement('div');
                card.id = `match-${eid}`;
                card.className = 'match-result-card' + (isFav ? ' favorited' : '');
                
                // Формируем заголовок аналогично скриншоту
                const headerText = `${escapeHtml(match.league || '')}, ${escapeHtml(match.date || '')} ${escapeHtml(match.time || '')}`;
                
                card.innerHTML = `
                    <div class="result-header">
                        ${headerText}
                    </div>
                    <div class="result-body">
                        <div class="team-block home">
                            <div class="team-name">${t1}</div>
                            <div class="team-logo">${init1}</div>
                        </div>
                        
                        <div class="score-block">
                            <div class="score-row">
                                <div class="score-box">${escapeHtml(score1)}</div>
                                <div class="score-box">${escapeHtml(score2)}</div>
                            </div>
                            <div class="match-status-text">Завершен</div>
                        </div>
                        
                        <div class="team-block away">
                            <div class="team-logo">${init2}</div>
                            <div class="team-name">${t2}</div>
                        </div>
                    </div>
                `;
                return card;
            }

            // --- Стандартная карточка для активных матчей ---
            const matchUrl = match.match_url || match.match_url_marathon || '';
            const googleQuery = encodeURIComponent(`${match.team1 || ''} ${match.team2 || ''} ${match.date || ''} результат матча`);
            const resultLink = `<a class="result-link" style="opacity:0.6; pointer-events:none;" href="#" title="Матч еще не начался">⏳ Ожидается</a>`;
            const scoreHtml = '';
            
            function oddBtn(label, value) {
                const raw = value || '';
                const unavail = !raw || raw === '—' || raw === '-' || raw === '0.00';
                const val = escapeHtml(unavail ? '—' : raw);
                const dt = escapeHtml((match.date || 'Сегодня') + ' ' + (match.time || ''));
                const lg = escapeHtml(match.league || '');
                if (unavail) return `<div class="odd-item odd-item--na" data-bet="${label}"><div class="odd-label">${label}</div><div class="odd-value">${val}</div></div>`;
                return `<div class="odd-item" data-bet="${label}" onclick="openBetSlip('${eid}','${teams.replace(/'/g,"\\'")   }','${label}','${val}','${dt}','${lg}')"><div class="odd-label">${label}</div><div class="odd-value">${val}</div></div>`;
            }
            
            const card = document.createElement('div');
            card.id = `match-${eid}`;
            card.className = 'match-card' + (isFav ? ' favorited' : '');
            card.innerHTML = `
                <div class="match-header">
                    <a class="match-id" href="#match-${eid}" onclick="shareMatch('${eid}','${teams.replace(/'/g,"\\'") }','${escapeHtml((match.date||'Сегодня')+' '+(match.time||''))}');return false;" title="ID: ${eid}">#${shortId}</a>
                    <div class="match-meta" style="display:flex;align-items:center;gap:4px;">
                        ${scoreHtml}
                        ${resultLink}
                    </div>
                    <div class="match-actions">
                        <button class="share-btn" onclick="shareMatch('${eid}','${teams.replace(/'/g,"\\'")}','${escapeHtml((match.date||'Сегодня')+' '+(match.time||''))}')" aria-label="Поделиться матчем" title="Поделиться матчем">🔗</button>
                        <button class="favorite-btn ${isFav?'active':''}" onclick="toggleFavorite('${eid}')" aria-label="${isFav?'Убрать из избранного':'В избранное'}" title="${isFav?'Убрать из избранного':'В избранное'}">★</button>
                    </div>
                </div>
                <div class="match-time">${escapeHtml(match.date||'Сегодня')} ${escapeHtml(match.time||'')}${countdown?`<span class="countdown">${countdown}</span>`:''}</div>
                <div class="match-teams">${t1} <span class="vs">—</span> ${t2}</div>
                <div class="odds-container">
                    <div class="odds-section-title">Основные</div>
                    ${oddBtn('П1',match.p1)}${oddBtn('X',match.x)}${oddBtn('П2',match.p2)}
                    ${(match.sport||'')==='football'?`<div class="odds-section-title">Двойной шанс</div>${oddBtn('1X',match.p1x)}${oddBtn('12',match.p12)}${oddBtn('X2',match.px2)}`:''}
                    ${(match.total_over && match.total_over!=='0.00' && match.total_value) ? `<div class="odds-section-title">Тотал (${match.total_value})</div>${oddBtn('ТБ '+match.total_value, match.total_over)}${oddBtn('ТМ '+match.total_value, match.total_under)}` : ''}
                </div>`;
            return card;
        }

        // ── Обновление коэффициентов на месте (без перестройки DOM) ──
        function patchCardOdds(card, match, favorites) {
            const eid = match.id || '';
            const isFav = favorites.includes(match.id);
            if (isFav) card.classList.add('favorited'); else card.classList.remove('favorited');
            const favBtn = card.querySelector('.favorite-btn');
            if (favBtn) { favBtn.classList.toggle('active', isFav); favBtn.title = isFav ? 'Убрать из избранного' : 'В избранное'; }
            
            // Update score
            let meta = card.querySelector('.match-meta');
            let scoreTag = card.querySelector('.match-score');
            if (match.score) {
                if (!scoreTag && meta) {
                    scoreTag = document.createElement('span');
                    scoreTag.className = 'match-score';
                    meta.prepend(scoreTag);
                }
                if (scoreTag) {
                    const hollowScore = `📋 Счёт: <span>${escapeHtml(match.score)}</span>`;
                    if (scoreTag.innerHTML !== hollowScore) {
                        scoreTag.innerHTML = hollowScore;
                        scoreTag.classList.add('highlight-pulse');
                        setTimeout(() => scoreTag.classList.remove('highlight-pulse'), 1500);
                    }
                }
            } else if (scoreTag) {
                scoreTag.remove();
            }
            
            const oddMap = { 
                'П1': match.p1, 'X': match.x, 'П2': match.p2, 
                '1X': match.p1x, '12': match.p12, 'X2': match.px2,
                ['ТБ '+match.total_value]: match.total_over,
                ['ТМ '+match.total_value]: match.total_under
            };
            card.querySelectorAll('[data-bet]').forEach(btn => {
                const betType = btn.getAttribute('data-bet');
                const newRaw = oddMap[betType] || '';
                const unavail = !newRaw || newRaw === '—' || newRaw === '-' || newRaw === '0.00';
                const newVal = unavail ? '—' : newRaw;
                const valEl = btn.querySelector('.odd-value');
                if (!valEl) return;
                if (valEl.textContent !== newVal) {
                    valEl.textContent = newVal;
                    // Вспышка — коэффициент изменился
                    valEl.classList.remove('odd-changed');
                    void valEl.offsetWidth; // reflow для перезапуска анимации
                    valEl.classList.add('odd-changed');
                    setTimeout(() => valEl.classList.remove('odd-changed'), 900);
                }
                // Обновляем onclick если значение изменилось
                if (!unavail) {
                    const t1 = escapeHtml(match.team1 || '');
                    const t2 = escapeHtml(match.team2 || '');
                    const teams = `${t1} vs ${t2}`;
                    const dt = escapeHtml((match.date || 'Сегодня') + ' ' + (match.time || ''));
                    const lg = escapeHtml(match.league || '');
                    btn.onclick = () => openBetSlip(eid, teams, betType, newVal, dt, lg);
                    btn.className = 'odd-item';
                } else {
                    btn.onclick = null;
                    btn.className = 'odd-item odd-item--na';
                }
            });
        }

        // ===== MY BETS LOGIC =====
        function toggleMyBets() {
            const modal = document.getElementById('myBetsModal');
            if (modal.classList.contains('show')) {
                modal.classList.remove('show');
                setTimeout(() => modal.style.display = 'none', 300);
            } else {
                modal.style.display = 'flex';
                // Trigger reflow
                void modal.offsetWidth;
                modal.classList.add('show');
                document.getElementById('walletInput').focus();
            }
        }

        async function checkMyBets() {
            const val = document.getElementById('walletInput').value.trim();
            const container = document.getElementById('betsListContainer');
            if (!val) {
                container.innerHTML = '<div style="text-align:center; color: var(--red);">Введите адрес кошелька или Telegram ID</div>';
                return;
            }
            container.innerHTML = '<div style="text-align:center; color: var(--accent);"><span class="loading"></span> Загрузка...</div>';
            
            try {
                // Fetch bets.json (cache busted)
                const r = await fetch('bets.json?t=' + Date.now());
                if (!r.ok) throw new Error('Network error');
                const data = await r.json();
                const bets = Array.isArray(data) ? data : (data.bets || []);
                
                // Filter bets by sender (PRIZM address) or tg_id
                const myBets = bets.filter(b => 
                    (b.sender && b.sender.toUpperCase() === val.toUpperCase()) || 
                    (b.tg_id && b.tg_id === val)
                );

                if (myBets.length === 0) {
                    container.innerHTML = '<div style="text-align:center; color: var(--text-secondary); margin-top:20px;">Ставки не найдены 🥺</div>';
                    return;
                }

                // Render bets (reversed for newest first)
                let html = '';
                [...myBets].reverse().forEach(b => {
                    const statusClass = b.status === 'win' ? 'bet-status-win' : (b.status === 'loss' ? 'bet-status-loss' : 'bet-status-pending');
                    const statusIcon = b.status === 'win' ? '✅ Выигрыш' : (b.status === 'loss' ? '❌ Проигрыш' : '⏳ В игре');
                    
                    html += `
                        <div class="bet-item ${statusClass}">
                            <div style="display:flex; justify-content:space-between; margin-bottom: 6px;">
                                <strong style="color:#fff;">${escapeHtml(b.team1)} vs ${escapeHtml(b.team2)}</strong>
                                <span style="font-size:0.8rem; font-weight:600;">${statusIcon}</span>
                            </div>
                            <div style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.6;">
                                Исход: <strong style="color:var(--accent-bright);">${escapeHtml(b.bet_type)}</strong> @ ${b.coef}<br>
                                Ставка: <strong style="color:#fff;">${b.amount} PRIZM</strong><br>
                                Выплата: <strong style="color: ${b.status === 'win' ? 'var(--green-bright)' : '#fff'};">${b.payout} PRIZM</strong><br>
                                <em>${escapeHtml(b.time || '')}</em>
                            </div>
                        </div>
                    `;
                });
                container.innerHTML = html;

            } catch (e) {
                container.innerHTML = '<div style="text-align:center; color: var(--red); margin-top:20px;">Ошибка загрузки базы ставок. Возможно, их пока нет.</div>';
                console.error(e);
            }
        }

        // Close modal on click outside
        document.getElementById('myBetsModal').addEventListener('click', (e) => {
            if (e.target.id === 'myBetsModal') toggleMyBets();
        });

        // ── Главная функция рендера — умный in-place update ──────
        function renderMatches(allMatches) {
            window.__LAST_ALL_MATCHES__ = window.__ALL_MATCHES__;
            window.__ALL_MATCHES__ = allMatches;
            checkFinishedFavorites(allMatches);

            const state = getFilterState();
            let filtered = filterMatches(allMatches, state);
            filtered = sortMatches(filtered, state.sort);
            buildGameFilter(allMatches);
            updateStats(filtered);

            const favorites = state.favs;
            const content = document.getElementById('content');

            if (!filtered.length) {
                content.innerHTML = '<div class="section"><p style="text-align:center;color:var(--text-tertiary);font-weight:500;">Матчи не найдены. Измените фильтры.</p></div>';
                return;
            }

            // Сохраняем позицию скролла ДО любых изменений
            const scrollY = window.scrollY || window.pageYOffset || 0;

            const leagues = {};
            const leagueOrder = [];
            filtered.forEach(m => {
                if (!leagues[m.league]) {
                    leagues[m.league] = [];
                    leagueOrder.push(m.league);
                }
                leagues[m.league].push(m);
            });

            // Убираем спиннер и прочие не-секции (например, начальный div "Загрузка линии...")
            content.querySelectorAll(':scope > :not(.section)').forEach(el => el.remove());

            // Карта уже отрисованных карточек
            const existingCards = {};
            content.querySelectorAll('.match-card[id], .match-result-card[id]').forEach(c => {
                existingCards[c.id.replace('match-', '')] = c;
            });

            // Карта существующих секций
            const existingSections = {};
            content.querySelectorAll('.section').forEach(sec => {
                const h2 = sec.querySelector('.section-title');
                if (h2) existingSections[h2.textContent] = sec;
            });

            const newIds = new Set(filtered.map(m => m.id));

            // Удаляем карточки матчей, которых нет в новой выборке
            Object.keys(existingCards).forEach(mid => {
                if (!newIds.has(mid)) { existingCards[mid].remove(); delete existingCards[mid]; }
            });

            let sectionIndex = 0;
            for (const league of leagueOrder) {
                const matches = leagues[league];
                let section = existingSections[league];
                if (!section) {
                    section = document.createElement('div');
                    section.className = 'section';
                    section.style.animationDelay = `${sectionIndex * 0.05}s`;
                    section.innerHTML = `<h2 class="section-title">${escapeHtml(league)}</h2>`;
                }
                // Always re-append to force correct order
                content.appendChild(section);
                matches.forEach(match => {
                    const existingCard = existingCards[match.id];
                    if (existingCard) {
                        const isResultNow = existingCard.classList.contains('match-result-card');
                        const shouldBeResult = !!match.score;
                        
                        if (isResultNow !== shouldBeResult) {
                            // Статус матча изменился, пересоздаем карточку
                            const newCard = createMatchCard(match, favorites);
                            existingCard.replaceWith(newCard);
                            // Чтобы appendChild добавил правильный элемент в конец (для сортировки)
                            section.appendChild(newCard);
                            existingCards[match.id] = newCard;
                        } else {
                            if (!shouldBeResult) {
                                patchCardOdds(existingCard, match, favorites);
                            } else {
                                // Если это уже завершенный матч, можно обновить счет при необходимости,
                                // но пока просто оставляем как есть или пересоздаем если нужно.
                                // Для надежности можно просто пересоздать, если счет изменился во время "Завершен", 
                                // но обычно он не меняется. Главное добавить в секцию:
                            }
                            section.appendChild(existingCard);
                        }
                    } else {
                        section.appendChild(createMatchCard(match, favorites));
                    }
                });
                sectionIndex++;
            }

            // Убираем секции без карточек
            content.querySelectorAll('.section').forEach(sec => {
                if (sec.querySelectorAll('.match-card, .match-result-card').length === 0) sec.remove();
            });

            // Восстанавливаем скролл — страница не прыгает при обновлении
            if (scrollY > 0) {
                requestAnimationFrame(() => { window.scrollTo(0, scrollY); });
            }
        }

        // Функция shareMatch для шаринга

        function shareMatch(id, teams, datetime) {
            const url = window.location.origin + window.location.pathname + '#match-' + id;
            navigator.clipboard.writeText(url).then(() => {
                showToast('Ссылка на матч скопирована!');
                if (navigator.vibrate) navigator.vibrate(30);
                // Подсвечиваем карточку
                const el = document.getElementById('match-' + id);
                if (el) {
                    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    el.classList.add('highlight-pulse');
                    setTimeout(() => el.classList.remove('highlight-pulse'), 1500);
                }
            }).catch(() => {
                showToast('#' + id + ' — ' + teams + ' ' + datetime);
            });
        }

        // ===== BET SLIP LOGIC =====
        let currentBet = null;

        function openBetSlip(id, teams, betType, coef, datetime, league) {
            currentBet = { id, teams, betType, coef, datetime, league };

            document.getElementById('bsMatch').textContent = teams;
            document.getElementById('bsMeta').textContent = `${league} • #${id} • ${datetime}`;
            document.getElementById('bsOutcome').textContent = betType;
            document.getElementById('bsCoef').textContent = coef;

            // Сброс инпута и выплаты
            const input = document.getElementById('bsInput');
            input.value = '';
            document.getElementById('bsPayout').textContent = '0.00';

            // Показываем купон
            document.getElementById('betSlip').classList.add('show');

            // Фокус на инпут для удобства (на мобильных может вызывать клаву)
            setTimeout(() => input.focus(), 300);
        }

        function closeBetSlip() {
            document.getElementById('betSlip').classList.remove('show');
            currentBet = null;
        }

        function calcPayout() {
            if (!currentBet) return;
            const amt = parseFloat(document.getElementById('bsInput').value) || 0;
            const c = parseFloat(currentBet.coef) || 0;
            const payout = amt * c;
            document.getElementById('bsPayout').textContent = payout > 0 ? payout.toFixed(2) : '0.00';
        }

        function copyBetSlipData() {
            if (!currentBet) return;
            const amt = document.getElementById('bsInput').value.trim() || '0';
            const matchLink = window.location.origin + window.location.pathname + '#match-' + currentBet.id;
            const msg = `${currentBet.teams}, ${currentBet.betType} @ ${currentBet.coef}\nСтавка: ${amt} PRIZM\nВремя события: ${currentBet.datetime}\nСсылка: ${matchLink}`;

            navigator.clipboard.writeText(msg).then(() => {
                // Сохраняем в локальную историю
                const payout = (parseFloat(amt) || 0) * (parseFloat(currentBet.coef) || 0);
                saveBetToHistory({
                    timestamp: Date.now(),
                    teams: currentBet.teams,
                    betType: currentBet.betType,
                    coef: currentBet.coef,
                    amount: amt || '0',
                    payout: payout
                });

                closeBetSlip();
                showToast('✅ Данные скопированы!');
                if (navigator.vibrate) navigator.vibrate(50);
                
                // Visual feedback on the button if it's still visible
                const btn = event?.target;
                if (btn && btn.classList.contains('bet-action-btn')) {
                    const originalText = btn.innerHTML;
                    btn.innerHTML = '✅ Скопировано!';
                    btn.style.background = 'var(--green)';
                    setTimeout(() => {
                        btn.innerHTML = originalText;
                        btn.style.background = '';
                    }, 2000);
                }
            });
        }

        // ===== HISTORY LOGIC =====
        function getHistory() {
            try { return JSON.parse(localStorage.getItem('prizmbet_history')) || []; }
            catch { return []; }
        }

        function saveBetToHistory(betItem) {
            const h = getHistory();
            h.unshift(betItem);
            if (h.length > 50) h.pop(); // Храним только последние 50 ставок
            localStorage.setItem('prizmbet_history', JSON.stringify(h));
        }

        function openHistory() {
            const list = document.getElementById('historyList');
            const history = getHistory();

            if (!history.length) {
                list.innerHTML = '<div style="text-align:center; padding: 30px 10px; color: var(--text-tertiary);">Вы еще не делали ставок.</div>';
            } else {
                list.innerHTML = history.map(h => {
                    const dt = new Date(h.timestamp).toLocaleString('ru-RU', {
                        day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
                    });
                    const payoutText = h.payout > 0 ? `+${h.payout.toFixed(2)} PZM` : '—';
                    return `
                        <div class="history-item">
                            <div class="history-item-header">
                                <span>🕒 ${dt}</span>
                                <span style="color: #fff;">${h.amount} PZM</span>
                            </div>
                            <div class="history-item-match">${escapeHtml(h.teams)}</div>
                            <div class="history-item-details">
                                <span class="history-item-bet">${escapeHtml(h.betType)} @ ${escapeHtml(h.coef)}</span>
                                <span class="history-item-payout">${payoutText}</span>
                            </div>
                        </div>
                    `;
                }).join('');
            }
            document.getElementById('historyModal').classList.add('show');
        }

        function closeHistory() {
            document.getElementById('historyModal').classList.remove('show');
        }

        function clearHistory() {
            if (confirm('Вы уверены, что хотите удалить локальную историю ставок?')) {
                localStorage.removeItem('prizmbet_history');
                openHistory();
            }
        }

        function onSearchInput() {
            if (window.__ALL_MATCHES__) renderMatches(window.__ALL_MATCHES__);
        }

        function copyWallet(btn) {
            const addr = document.getElementById('walletAddress').textContent;
            navigator.clipboard.writeText(addr).then(() => {
                showToast('💎 Адрес кошелька скопирован!');
                if (navigator.vibrate) navigator.vibrate(50);
                
                if (btn) {
                    const originalText = btn.innerHTML;
                    btn.innerHTML = '✅ Скопировано!';
                    btn.classList.add('btn-success');
                    setTimeout(() => {
                        btn.innerHTML = originalText;
                        btn.classList.remove('btn-success');
                    }, 2000);
                }
            });
        }

        function showToast(msg) {
            const t = document.getElementById('betToast');
            document.getElementById('betToastMessage').textContent = msg;
            t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), 3500);
        }

        function openImage(src) { window.open(src, '_blank'); }

        // Auto-refresh
        setInterval(loadData, AUTO_REFRESH_MS);
        document.addEventListener('visibilitychange', () => { if (!document.hidden) loadData(); });
        setInterval(() => { if (window.__ALL_MATCHES__) renderMatches(window.__ALL_MATCHES__); }, 60000);

        window.addEventListener('load', () => {
            updateNotifBell();
            loadData().then(() => {
                // После загрузки — проверяем якорь в URL
                if (window.location.hash && window.location.hash.startsWith('#match-')) {
                    setTimeout(() => {
                        const el = document.querySelector(window.location.hash);
                        if (el) {
                            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        }
                    }, 400);
                }
            }).catch(() => {
                if (window.location.hash && window.location.hash.startsWith('#match-')) {
                    setTimeout(() => {
                        const el = document.querySelector(window.location.hash);
                        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }, 800);
                }
            });
            wireFilters();
        });
