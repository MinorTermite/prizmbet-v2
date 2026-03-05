// Favorites management for PrizmBet

const STORAGE_KEY = 'prizmbet_favorites';
const DETAILS_KEY = 'prizmbet_fav_details';

export function getFavorites() {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
    } catch { return []; }
}

export function saveFavorites(favorites) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites));
}

export function getFavDetails() {
    try {
        return JSON.parse(localStorage.getItem(DETAILS_KEY)) || {};
    } catch { return {}; }
}

export function saveFavDetails(details) {
    localStorage.setItem(DETAILS_KEY, JSON.stringify(details));
}

export function toggleFavorite(matchId, matches = []) {
    let favorites = getFavorites();
    const index = favorites.indexOf(matchId);
    
    if (index > -1) {
        favorites.splice(index, 1);
    } else {
        favorites.push(matchId);
        // Save details for notifications
        if (matches.length > 0) {
            const match = matches.find(m => m.id === matchId);
            if (match) {
                let details = getFavDetails();
                details[matchId] = {
                    home: match.home_team,
                    away: match.away_team,
                    league: match.league,
                    time: match.match_time
                };
                saveFavDetails(details);
            }
        }
    }
    saveFavorites(favorites);
    return favorites;
}
