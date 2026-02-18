// PrizmBet v2 - Main App
let allMatches = [];

// Dark Theme
function initTheme() {
  const saved = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-theme", saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme");
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("theme", next);
}

// Filter matches
function filterMatches(search = "", league = "") {
  let filtered = allMatches;
  if (search) {
    const term = search.toLowerCase();
    filtered = filtered.filter(m => 
      (m.home_team || "").toLowerCase().includes(term) ||
      (m.away_team || "").toLowerCase().includes(term)
    );
  }
  if (league) {
    filtered = filtered.filter(m => m.league === league);
  }
  renderMatches(filtered);
}

function renderMatches(matches) {
  const container = document.getElementById("matches-container");
  if (!container) return;
  
  container.innerHTML = matches.map(m => `
    <div class="match-card">
      <div class="match-league">${m.league || ""}</div>
      <div class="match-teams">
        <span>${m.home_team || ""}</span> vs <span>${m.away_team || ""}</span>
      </div>
      <div class="match-time">${new Date(m.match_time).toLocaleString()}</div>
      <div class="match-odds">
        ${m.odds_home ? `<span>P1: ${m.odds_home}</span>` : ""}
        ${m.odds_draw ? `<span>X: ${m.odds_draw}</span>` : ""}
        ${m.odds_away ? `<span>P2: ${m.odds_away}</span>` : ""}
      </div>
    </div>
  `).join("");
}

async function loadMatches() {
  try {
    const response = await fetch("/matches.json");
    allMatches = await response.json();
    renderMatches(allMatches);
  } catch (error) {
    console.error("Error loading matches:", error);
  }
}

// Service Worker
function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/pwa/sw.js");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  loadMatches();
  registerServiceWorker();
});
