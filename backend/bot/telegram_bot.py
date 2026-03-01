#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRIZMBET Telegram Bot
Приём ставок через PRIZM кошелёк + уведомления

Установка:
  pip install python-telegram-bot apscheduler requests

Запуск:
  python telegram_bot.py
"""

import json
import sys
import logging
import os
import time
import asyncio
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)

import prizm_api

# ── Конфиг ──────────────────────────────────────────────────
BOT_TOKEN    = "8560914086:AAFGDc70pfIwBX0FhwQDWmFjcnnpVvKOxps"
ADMIN_ID     = 984705599
WALLET       = "PRIZM-4N7T-L2A7-RQZA-5BETW"
BETS_FILE    = Path(__file__).parent.parent.parent / "frontend" / "bets.json"
MATCHES_FILE = Path(__file__).parent.parent.parent / "frontend" / "matches.json"
CONFIG_FILE  = Path(__file__).parent / "bot_config.json"


def load_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8")) if CONFIG_FILE.exists() else {}
    except Exception:
        return {}

def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

def get_notify_ids() -> list[int]:
    """Вернуть список chat_id для уведомлений: всегда включает ADMIN_ID + сохранённые группы/каналы"""
    cfg = load_config()
    ids = [ADMIN_ID]
    group_id = cfg.get("group_chat_id")
    if group_id and group_id not in ids:
        ids.append(group_id)
    return ids

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ── Хранилище ставок ─────────────────────────────────────────
def load_bets() -> list:
    """Загрузить ставки. Поддерживает оба формата: plain list [] и {"bets": [...]}"""
    try:
        if not BETS_FILE.exists():
            return []
        data = json.loads(BETS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("bets", [])
        return []
    except Exception:
        return []

def save_bets(bets: list):
    """Сохранить ставки в формате совместимом с bet_parser.py и admin.html"""
    data = {
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_bets": len(bets),
        "bets": bets,
    }
    BETS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def load_matches() -> dict:
    """Загрузить матчи по ID для быстрого поиска"""
    try:
        data = json.loads(MATCHES_FILE.read_text(encoding="utf-8"))
        return {m["id"]: m for m in data.get("matches", [])}
    except Exception:
        return {}

# ── Хелперы ──────────────────────────────────────────────────
def get_main_keyboard(is_admin=False) -> ReplyKeyboardMarkup:
    """Вернуть главное меню кнопок"""
    buttons = [
        ["🎰 Сделать ставку", "📋 Мои ставки"],
        ["📖 Правила", "⭐ Преимущества"]
    ]
    if is_admin:
        buttons.append(["📊 Ставки (Админ)", "📈 Статистика (Админ)"])
        buttons.append(["💰 Баланс", "📢 Настройка канала"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def fmt_bet(bet: dict, idx: int = None) -> str:
    prefix = f"#{idx} " if idx is not None else ""
    status_emoji = {"pending": "⏳", "win": "✅", "loss": "❌", "cancelled": "🚫"}.get(bet.get("status"), "⏳")
    return (
        f"{prefix}{status_emoji} *{bet.get('team1','?')} — {bet.get('team2','?')}*\n"
        f"  Исход: `{bet.get('bet_type','?')}` | Коэф: `{bet.get('coef','?')}`\n"
        f"  Ставка: `{bet.get('amount',0):.1f} PRIZM` | "
        f"Выигрыш: `{bet.get('payout',0):.1f} PRIZM`\n"
        f"  Матч ID: `{bet.get('match_id','?')}`\n"
        f"  От: `{bet.get('sender','?')}`\n"
        f"  Время: {bet.get('time','?')}"
    )

# ── Команды бота ─────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_admin = (user.id == ADMIN_ID)
    
    text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "🎰 *PRIZMBET — Криптобукмекер*\n\n"
        "Как сделать ставку:\n"
        "1️⃣ Открой сайт: [minortermite.github.io/betprizm](https://minortermite.github.io/betprizm)\n"
        "2️⃣ Выбери матч\n"
        "3️⃣ *ПРОВЕРИТЬ СТАВКУ...* Удостовериться, что событие существует и коэффициенты соответствуют.\n"
        "4️⃣ Вернуться на сайт и нажать на коэффициент\n"
        "5️⃣ Скопируй сообщение для ставки (Пример: `Матч ЛЧ, Галатасарай — Ювентус, П1 @ 1.41`)\n"
        "6️⃣ Отправь монеты PRIZM на кошелёк:\n"
        f"   `{WALLET}`\n\n"
        "📌 Используйте кнопки меню для навигации."
    )
    await update.message.reply_text(
        text, 
        parse_mode="Markdown", 
        disable_web_page_preview=True,
        reply_markup=get_main_keyboard(is_admin)
    )

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Справка PRIZMBET*\n\n"
        "*Формат комментария* к транзакции:\n"
        "`ID_МАТЧА ТИП СУММА`\n\n"
        "🎯 *Обозначения ставок:*\n"
        "▸ `П1` — победа П1\n"
        "▸ `П2` — победа П2\n"
        "▸ `X` — ничья\n"
        "▸ `1X`, `X2`, `12` — двойные исходы\n\n"
        "*Пример:* отправь `10000 PRIZM` на кошелёк\n"
        f"`{WALLET}`\n"
        "с комментарием: `27080379 П1 10000`\n"
        "(_Матч ЛЧ, Галатасарай — Ювентус, П1 @ 1.41_)\n\n"
        "👉 Подробности: /rules"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_rules(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "📋 *ПРАВИЛА PRIZMBET*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💎 *Ставки принимаются только в монетах PRIZM*\n\n"
        "📊 *Лимиты:*\n"
        "• Минимальная ставка: `1 500 PRIZM`\n"
        "• Максимальная ставка: `200 000 PRIZM`\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🏷️ *Обозначения ставок:*\n"
        "• `П1` — победа 1-й команды (хозяева)\n"
        "• `П2` — победа 2-й команды (гости)\n"
        "• `X` — ничья\n"
        "• `1X` — победа хозяев или ничья\n"
        "• `X2` — победа гостей или ничья\n"
        "• `12` — победа любой команды (ничьи нет)\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *Как сделать ставку:*\n"
        "1️⃣ Выбери матч на сайте: [prizmbet](https://minortermite.github.io/betprizm/)\n"
        "2️⃣ Нажми на коэффициент — появится купон\n"
        "3️⃣ Скопируй сообщение для перевода\n"
        "4️⃣ Отправь PRIZM на кошелёк:\n"
        f"`{WALLET}`\n"
        "5️⃣ В комментарий вставь скопированное сообщение\n\n"
        "Пример комментария:\n"
        "`Галатасарай vs Ливерпуль 10 мар 20:45 П2 1.76`\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ *Важно:*\n"
        "• Ставки принимаются только *до начала* события\n"
        "• В случае проигрыша ставка *не возвращается*\n"
        "• При выигрыше — выплата по коэффициенту\n"
        "• Выплаты в течение 24 часов\n"
        "• Количество ставок ограничено\n"
        "• PRIZMBET вправе отказать в принятии ставки\n"
        "  и вернуть средства до начала события"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_advantages(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "⭐ *ПРЕИМУЩЕСТВА PRIZMBET*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "✅  *Не требуется верификация*\n"
        "    Никаких документов и паспортов\n\n"
        "🕵️  *Анонимные платежи без проверки KYC*\n"
        "    Полная конфиденциальность\n\n"
        "🔓  *Нет условий по минимальному обороту*\n"
        "    Выводи средства в любое время\n\n"
        "🌍  *Нет ограничений по гео*\n"
        "    Доступно из любой страны\n\n"
        "₿  *Баланс счёта в криптовалюте PRIZM*\n"
        "    Децентрализованная блокчейн-монета\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🎰 Начни играть: /start\n"
        "📋 Правила: /rules"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_mybets(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    bets = load_bets()
    my = [b for b in bets if b.get("tg_id") == user_id]
    if not my:
        await update.message.reply_text("У вас пока нет ставок.\n\nНапишите /start чтобы узнать как сделать ставку.")
        return
    lines = ["📋 *Ваши ставки:*\n"]
    for i, b in enumerate(reversed(my[-10:]), 1):
        lines.append(fmt_bet(b, i))
    await update.message.reply_text("\n\n".join(lines), parse_mode="Markdown")

async def cmd_bets(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Только для админа — все активные ставки"""
    if update.effective_user.id != ADMIN_ID:
        return
    bets = load_bets()
    pending = [b for b in bets if b.get("status") == "pending"]
    if not pending:
        await update.message.reply_text("Нет активных ставок ⏳")
        return
    lines = [f"📊 *Активных ставок: {len(pending)}*\n"]
    for i, b in enumerate(pending[-15:], 1):
        lines.append(fmt_bet(b, i))
    # Кнопки управления
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Обновить", callback_data="refresh_bets"),
        InlineKeyboardButton("📥 Проверить PRIZM", callback_data="check_prizm"),
    ], [
        InlineKeyboardButton("💰 Баланс кошелька", callback_data="check_balance"),
    ]])
    await update.message.reply_text("\n\n".join(lines), parse_mode="Markdown", reply_markup=kb)

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    bets = load_bets()
    total   = len(bets)
    pending = sum(1 for b in bets if b.get("status") == "pending")
    wins    = sum(1 for b in bets if b.get("status") == "win")
    losses  = sum(1 for b in bets if b.get("status") == "loss")
    income  = sum(b.get("amount", 0) for b in bets if b.get("status") in ("pending", "loss"))
    payouts = sum(b.get("payout", 0) for b in bets if b.get("status") == "win")
    profit  = income - payouts
    text = (
        f"📊 *Статистика PRIZMBET*\n\n"
        f"Всего ставок: `{total}`\n"
        f"⏳ Ожидают: `{pending}`\n"
        f"✅ Выиграли: `{wins}`\n"
        f"❌ Проиграли: `{losses}`\n\n"
        f"💰 Принято: `{income:.1f} PRIZM`\n"
        f"💸 Выплачено: `{payouts:.1f} PRIZM`\n"
        f"📈 Прибыль: `{profit:.1f} PRIZM`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_win(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Отметить ставку как выигрышную: /win <bet_id>"""
    if update.effective_user.id != ADMIN_ID:
        return
    args = ctx.args
    if not args:
        await update.message.reply_text("Использование: /win <ID_ставки>")
        return
    bets = load_bets()
    bet_id = args[0]
    for b in bets:
        if b.get("id") == bet_id:
            b["status"] = "win"
            save_bets(bets)
            await update.message.reply_text(f"✅ Ставка {bet_id} отмечена как ВЫИГРЫШ\nВыплата: {b.get('payout',0):.1f} PRIZM → {b.get('sender','?')}")
            # Уведомить игрока
            tg_id = b.get("tg_id")
            if tg_id:
                try:
                    await ctx.bot.send_message(
                        chat_id=int(tg_id),
                        text=f"🎉 *Ваша ставка выиграла!*\n\n{fmt_bet(b)}\n\nВыплата `{b.get('payout',0):.1f} PRIZM` будет отправлена на ваш кошелёк.",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
            return
    await update.message.reply_text(f"Ставка {bet_id} не найдена")

async def cmd_loss(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Отметить ставку как проигрышную: /loss <bet_id>"""
    if update.effective_user.id != ADMIN_ID:
        return
    args = ctx.args
    if not args:
        await update.message.reply_text("Использование: /loss <ID_ставки>")
        return
    bets = load_bets()
    bet_id = args[0]
    for b in bets:
        if b.get("id") == bet_id:
            b["status"] = "loss"
            save_bets(bets)
            await update.message.reply_text(f"❌ Ставка {bet_id} отмечена как ПРОИГРЫШ")
            tg_id = b.get("tg_id")
            if tg_id:
                try:
                    await ctx.bot.send_message(
                        chat_id=int(tg_id),
                        text=f"😔 *Ставка не сыграла*\n\n{fmt_bet(b)}\n\nУдачи в следующий раз!",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
            return
    await update.message.reply_text(f"Ставка {bet_id} не найдена")

async def cmd_balance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Проверить баланс кошелька PRIZM — только для админа"""
    if update.effective_user.id != ADMIN_ID:
        return
    msg = await update.message.reply_text("🔍 Запрашиваю баланс кошелька...")
    try:
        info = prizm_api.get_balance()
        if info["balance"] is None:
            await msg.edit_text("❌ Не удалось получить баланс — все ноды недоступны.")
            return
        text = (
            f"💰 *Баланс кошелька PRIZMBET*\n\n"
            f"Кошелёк: `{info['wallet']}`\n"
            f"Баланс: `{info['balance']:.2f} PRIZM`\n"
            f"Неподтверждённый: `{info['unconfirmed']:.2f} PRIZM`\n"
            f"Нода: `{info['node']}`"
        )
        await msg.edit_text(text, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {e}")


async def cmd_setgroup(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Установить группу/канал для уведомлений: /setgroup <chat_id>"""
    if update.effective_user.id != ADMIN_ID:
        return
    if not ctx.args:
        cfg = load_config()
        current = cfg.get("group_chat_id", "не задан")
        await update.message.reply_text(
            f"📢 *Канал/группа уведомлений*\n\n"
            f"Текущий: `{current}`\n\n"
            f"Чтобы задать:\n"
            f"1. Добавь бота в группу/канал как администратора\n"
            f"2. Напиши `/chatid` в той группе чтобы узнать ID\n"
            f"3. Затем: `/setgroup <chat_id>`",
            parse_mode="Markdown"
        )
        return
    try:
        chat_id = int(ctx.args[0])
        cfg = load_config()
        cfg["group_chat_id"] = chat_id
        save_config(cfg)
        await update.message.reply_text(f"✅ Канал/группа уведомлений задан: `{chat_id}`", parse_mode="Markdown")
        # Тест — отправляем пробное сообщение
        try:
            await ctx.bot.send_message(
                chat_id=chat_id,
                text="✅ *PRIZMBET* — уведомления подключены!\n\nЯ буду сообщать сюда о новых транзакциях.",
                parse_mode="Markdown"
            )
        except Exception as e:
            await update.message.reply_text(f"⚠️ Не удалось отправить тест: {e}\nПроверь, добавлен ли бот в группу/канал.")
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Пример: `/setgroup -1001234567890`", parse_mode="Markdown")


async def cmd_chatid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Показать ID текущего чата (для настройки группы/канала)"""
    chat = update.effective_chat
    await update.message.reply_text(
        f"💬 Chat ID: `{chat.id}`\n"
        f"Тип: `{chat.type}`\n"
        f"Название: `{chat.title or chat.username or '—'}`\n\n"
        f"Скопируй этот ID и отправь боту: `/setgroup {chat.id}`",
        parse_mode="Markdown"
    )

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "refresh_bets":
        await cmd_bets(update, ctx)
    elif q.data == "check_prizm":
        await q.message.reply_text("🔍 Проверяю транзакции PRIZM...")
        await check_prizm_transactions(ctx.bot)
    elif q.data == "check_balance":
        try:
            info = prizm_api.get_balance()
            if info["balance"] is None:
                await q.message.reply_text("❌ Не удалось получить баланс — все ноды недоступны.")
            else:
                text = (
                    f"💰 *Баланс кошелька*\n\n"
                    f"`{info['wallet']}`\n"
                    f"Баланс: `{info['balance']:.2f} PRIZM`\n"
                    f"Неподтверждённый: `{info['unconfirmed']:.2f} PRIZM`"
                )
                await q.message.reply_text(text, parse_mode="Markdown")
        except Exception as e:
            await q.message.reply_text(f"❌ Ошибка: {e}")


# ── Обработка текстовых кнопок ───────────────────────────────
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🎰 Сделать ставку":
        await cmd_start(update, ctx)
    elif text == "📋 Мои ставки":
        await cmd_mybets(update, ctx)
    elif text == "📖 Правила":
        await cmd_rules(update, ctx)
    elif text == "⭐ Преимущества":
        await cmd_advantages(update, ctx)
    elif text == "📊 Ставки (Админ)":
        await cmd_bets(update, ctx)
    elif text == "📈 Статистика (Админ)":
        await cmd_stats(update, ctx)
    elif text == "💰 Баланс":
        await cmd_balance(update, ctx)
    elif text == "📢 Настройка канала":
        await cmd_setgroup(update, ctx)

# ── Проверка транзакций PRIZM (запускается по расписанию) ────
async def check_prizm_transactions(bot=None):
    """Читает новые транзакции и создаёт ставки"""
    log.info("Checking PRIZM transactions...")
    new_txs = prizm_api.get_new_transactions()
    if not new_txs:
        log.info("No new transactions")
        return

    bets    = load_bets()
    matches = load_matches()
    bet_ids = {b.get("tx_id") for b in bets}
    added   = 0

    for tx in new_txs:
        tx_id   = tx.get("transaction", "")
        if tx_id in bet_ids:
            continue

        # Пропускаем исходящие транзакции
        if tx.get("senderRS") == WALLET:
            continue

        amount = prizm_api.prizm_amount(tx)
        sender = prizm_api.get_sender_address(tx)

        # Пробуем прочитать plain-text сообщение
        comment = prizm_api.get_message(tx)
        parsed  = prizm_api.parse_bet_comment(comment)

        if not parsed:
            # Транзакция без распознаваемой ставки
            has_enc = prizm_api.has_encrypted_message(tx)
            if has_enc and bot:
                enc_text = (
                    f"💸 *Входящий перевод* (сообщение зашифровано)\n\n"
                    f"От: `{sender}`\n"
                    f"Сумма: `{amount:.2f} PRIZM`\n"
                    f"TX: `{tx_id[:16]}...`\n\n"
                    f"⚠️ Ставка не распознана — сообщение зашифровано.\n"
                    f"Попросите игрока прислать *незашифрованный* комментарий."
                )
                for cid in get_notify_ids():
                    try:
                        await bot.send_message(chat_id=cid, text=enc_text, parse_mode="Markdown")
                    except Exception as e:
                        log.error(f"Notify {cid} error: {e}")
            else:
                log.info(f"TX {tx_id[:12]}: no bet comment '{comment}'")
            bet_ids.add(tx_id)
            continue

        match_id = parsed["match_id"]
        bet_type = parsed["bet_type"]

        # Найти матч и коэффициент
        match = matches.get(match_id, {})
        coef = prizm_api.get_coef(match, bet_type)
        payout = round(amount * coef, 2) if coef > 0 else 0

        bet = {
            "id":       f"BET{int(time.time())}{added}",
            "tx_id":    tx_id,
            "match_id": match_id,
            "team1":    match.get("team1", "?"),
            "team2":    match.get("team2", "?"),
            "league":   match.get("league", ""),
            "bet_type": bet_type,
            "coef":     coef,
            "amount":   amount,
            "payout":   payout,
            "sender":   sender,
            "tg_id":    "",
            "status":   "pending",
            "time":     datetime.now().strftime("%d.%m.%Y %H:%M"),
        }
        bets.append(bet)
        bet_ids.add(tx_id)
        added += 1
        log.info(f"New bet: {bet['id']} — {match.get('team1','?')} {bet_type} {amount} PRIZM")

        # Уведомить всех (админ + группа/канал)
        if bot:
            bet_text = (
                f"🎰 *Новая ставка!*\n\n"
                f"{fmt_bet(bet)}\n\n"
                f"✅ `/win {bet['id']}`\n"
                f"❌ `/loss {bet['id']}`"
            )
            notify_ids = get_notify_ids()
            log.info(f"Target notify IDs: {notify_ids}")
            for cid in notify_ids:
                try:
                    await bot.send_message(chat_id=cid, text=bet_text, parse_mode="Markdown")
                    log.info(f"Notification sent to {cid}")
                except Exception as e:
                    log.error(f"Notify {cid} error: {e}")
                    # Если админа не может уведомить — это плохо
                    if cid == ADMIN_ID:
                        log.critical(f"Admin notification failed! Check BOT_TOKEN or if bot is blocked.")

    if added:
        save_bets(bets)
        log.info(f"Saved {added} new bets")

# ── Запуск ───────────────────────────────────────────────────
def main():
    if not BOT_TOKEN:
        log.critical("ERROR: BOT_TOKEN is not set in environment variables!")
        print("\n\033[91mCRITICAL ERROR: BOT_TOKEN is not set!\033[0m")
        print("Please set the BOT_TOKEN environment variable before running the bot.")
        print("Example: set BOT_TOKEN=your_token_here (Windows) or export BOT_TOKEN=your_token_here (Linux/Mac)")
        sys.exit(1)

    log.info("Starting PRIZMBET Bot...")
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("help",       cmd_help))
    app.add_handler(CommandHandler("rules",      cmd_rules))
    app.add_handler(CommandHandler("advantages", cmd_advantages))
    app.add_handler(CommandHandler("mybets",     cmd_mybets))
    app.add_handler(CommandHandler("bets",       cmd_bets))
    app.add_handler(CommandHandler("stats",      cmd_stats))
    app.add_handler(CommandHandler("win",        cmd_win))
    app.add_handler(CommandHandler("loss",       cmd_loss))
    app.add_handler(CommandHandler("balance",    cmd_balance))
    app.add_handler(CommandHandler("setgroup",   cmd_setgroup))
    app.add_handler(CommandHandler("chatid",     cmd_chatid))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # Обработчик текстовых кнопок
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # Проверка PRIZM транзакций каждые 5 минут
    async def _check_tx_job(ctx: ContextTypes.DEFAULT_TYPE):
        await check_prizm_transactions(ctx.bot)

    app.job_queue.run_repeating(_check_tx_job, interval=300, first=30)

    log.info(f"Bot started | Admin: {ADMIN_ID} | Wallet: {WALLET}")
    log.info(f"Initial notify IDs: {get_notify_ids()}")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
