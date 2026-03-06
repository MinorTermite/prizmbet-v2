/**
 * PrizmBet v2 - Bet Slip Module
 */
import { showToast } from './notifications.js';

export let currentBet = null;

export function setBet(data) {
    currentBet = data;
}

export function closeBetSlip() {
    const slip = document.getElementById('betSlip');
    if (slip) slip.classList.remove('active');
}

export function openBetSlip(betData, betType, coef) {
    const slip = document.getElementById('betSlip');
    if (!slip) return;
    
    currentBet = betData;
    
    document.getElementById('bsMatch').textContent = betData.teams;
    document.getElementById('bsMeta').textContent = `${betData.league} • #${betData.id}`;
    document.getElementById('bsOutcome').textContent = betType;
    document.getElementById('bsCoef').textContent = coef;
    
    slip.classList.add('active');
    calcPayout();
}

export function calcPayout() {
    const input = document.getElementById('bsInput');
    const coef = document.getElementById('bsCoef');
    const payout = document.getElementById('bsPayout');
    if (!input || !coef || !payout) return;
    
    const amount = parseFloat(input.value) || 0;
    const c = parseFloat(coef.textContent) || 0;
    payout.textContent = (amount * c).toFixed(2);
}

function _copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        return navigator.clipboard.writeText(text).catch(() => {
            _copyFallback(text);
        });
    }
    _copyFallback(text);
    return Promise.resolve();
}

function _copyFallback(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try { document.execCommand('copy'); } catch (_) {}
    document.body.removeChild(ta);
}

export function copyBetSlipData() {
    if (!currentBet) return;
    const amtInput = document.getElementById('bsInput');
    const amt = amtInput ? amtInput.value.trim() : '0';
    const matchLink = `${window.location.origin}${window.location.pathname}#match-${currentBet.id}`;
    const amtPart = amt && amt !== '0' ? ` | ${amt} PZM` : '';
    const msg = `${currentBet.teams}, ${currentBet.betType} @ ${currentBet.coef}${amtPart}\n${currentBet.datetime} ${matchLink}`;

    // Show feedback on button, then close
    const btn = document.querySelector('#betSlip .bet-action-btn');
    if (btn) {
        const orig = btn.innerHTML;
        btn.innerHTML = '✅ Скопировано!';
        btn.disabled = true;
        setTimeout(() => { btn.innerHTML = orig; btn.disabled = false; }, 1200);
    }

    _copyText(msg).then(() => {
        showToast('✅ Данные скопированы!');
        setTimeout(() => {
            closeBetSlip();
            // Notify app for history saving
            window.dispatchEvent(new CustomEvent('betPlaced', {
                detail: { ...currentBet, amount: amt, timestamp: Date.now() }
            }));
        }, 900);
    });
}

export function toggleMyBets() {
    const modal = document.getElementById('myBetsModal');
    if (modal) modal.classList.toggle('active');
}

export async function checkMyBets() {
    const val = document.getElementById('walletInput')?.value.trim();
    const container = document.getElementById('betsListContainer');
    if (!val || !container) return;
    
    container.innerHTML = '<div style="text-align:center; color: var(--accent);"><span class="loading"></span> Загрузка...</div>';
    
    try {
        const r = await fetch('bets.json?t=' + Date.now());
        const data = await r.json();
        const bets = Array.isArray(data) ? data : (data.bets || []);
        
        const myBets = bets.filter(b => 
            (b.sender && b.sender.toUpperCase() === val.toUpperCase()) || 
            (b.tg_id && b.tg_id === val)
        );

        if (myBets.length === 0) {
            container.innerHTML = '<div style="text-align:center; color: var(--text-secondary); margin-top:20px;">Ставки не найдены 🥺</div>';
            return;
        }

        let html = '';
        [...myBets].reverse().forEach(b => {
            const statusClass = b.status === 'win' ? 'bet-status-win' : (b.status === 'loss' ? 'bet-status-loss' : 'bet-status-pending');
            const statusIcon = b.status === 'win' ? '✅ Выигрыш' : (b.status === 'loss' ? '❌ Проигрыш' : '⏳ В игре');
            
            html += `
                <div class="bet-item ${statusClass}">
                    <div style="display:flex; justify-content:space-between; margin-bottom: 6px;">
                        <strong style="color:#fff;">${b.team1} vs ${b.team2}</strong>
                        <span style="font-size:0.8rem; font-weight:600;">${statusIcon}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.6;">
                        Исход: <strong style="color:var(--accent-bright);">${b.bet_type}</strong> @ ${b.coef}<br>
                        Ставка: <strong style="color:#fff;">${b.amount} PRIZM</strong><br>
                        Выплата: <strong style="color: ${b.status === 'win' ? 'var(--green-bright)' : '#fff'};">${b.payout} PRIZM</strong><br>
                        <em>${b.time || ''}</em>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<div style="text-align:center; color: var(--red); margin-top:20px;">Ошибка загрузки базы ставок.</div>';
    }
}

export function copyWallet(btn) {
    const address = "PRIZM-4N7T-L2A7-RQZA-5BETW";
    _copyText(address).then(() => {
        const originalText = btn.innerHTML;
        btn.innerHTML = "✅ Скопировано!";
        setTimeout(() => btn.innerHTML = originalText, 2000);
    });
}
