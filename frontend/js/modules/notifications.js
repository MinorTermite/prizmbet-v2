// Notification management for PrizmBet
import { getFavDetails, saveFavDetails } from './favorites.js';

export async function requestNotificationPermission() {
    if (!("Notification" in window)) return false;
    if (Notification.permission === "granted") return true;
    
    const permission = await Notification.requestPermission();
    return permission === "granted";
}

export function playNotificationSound() {
    try {
        const audio = new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3');
        audio.play();
    } catch (e) { console.error("Sound play failed", e); }
}

export function showNotification(title, body) {
    if (Notification.permission === "granted") {
        new Notification(title, { body, icon: '/prizmbet-logo.webp' });
        playNotificationSound();
    }
}

export function checkFinishedFavorites(allMatches) {
    const details = getFavDetails();
    const favIds = Object.keys(details);
    if (favIds.length === 0) return;

    allMatches.forEach(match => {
        if (favIds.includes(match.id) && match.score) {
            showNotification(
                "Матч завершен! 🏆",
                `${match.home_team} ${match.score} ${match.away_team}`
            );
            // Remove from details to not notify again
            delete details[match.id];
            saveFavDetails(details);
        }
    });
}
