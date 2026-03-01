// ==========================================
// PRIZMBET SMOKE TESTS
// Легковесные assert-проверки для защиты критического пути
// ==========================================

function runSmokeTests() {
    console.log('[Tests] Запуск базовых Smoke Tests...');

    // 1. Проверка API функций (загружены ли они из api.js)
    console.assert(typeof loadData === 'function', '[Ошибка] loadData не найдена. api.js не загружен?');
    console.assert(typeof isDataStale === 'function', '[Ошибка] isDataStale не найдена.');

    // 2. Проверка чистых функций фильтрации
    if (typeof filterMatches === 'function') {
        const mockMatches = [
            { id: '1', team1: 'Real', team2: 'Barca', league: 'Испания. Ла Лига', p1: '2.0', p2: '3.0' }, // valid
            { id: '2', team1: 'Lakers', team2: 'Bulls', league: 'NBA', sport: 'basketball' }, // valid
            { id: '3', team1: 'Team A', team2: '-', league: 'invalid' } // invalid (team2 is -)
        ];

        const filtersAll = { q: '', sport: 'all', game: 'all', pop: false, favOnly: false, favs: [] };
        const res = filterMatches(mockMatches, filtersAll);

        // isValidMatch will drop the 3rd match.
        console.assert(res.length === 2, '[Ошибка] filterMatches неверно отсеивает невалидные матчи.');

        const filtersBasket = { ...filtersAll, sport: 'basketball' };
        const resBasket = filterMatches(mockMatches, filtersBasket);
        console.assert(resBasket.length === 1 && resBasket[0].sport === 'basketball', '[Ошибка] filterMatches неверно фильтрует по спорту.');
    } else {
        console.warn('[Tests] filterMatches не найдена для тестирования.');
    }

    // 3. Проверка Купона Ставок (Bet Slip DOM и логика)
    const bs = document.getElementById('betSlip');
    console.assert(bs !== null, '[Ошибка] DOM-элемент #betSlip не найден!');
    const bsInput = document.getElementById('bsInput');
    console.assert(bsInput !== null, '[Ошибка] Поле ввода #bsInput не найдено!');

    // 4. Проверка предотвращения множественных рендеров (Diff check preparedness)
    const content = document.getElementById('content');
    console.assert(content !== null, '[Ошибка] Контейнер #content не найден.');

    console.log('[Tests] Проверки завершены ✅');
}

// Запускаем после загрузки DOM и начального рендера
window.addEventListener('load', () => {
    setTimeout(runSmokeTests, 2000);
});
