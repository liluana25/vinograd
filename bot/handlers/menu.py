"""Main menu and shared navigation."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.utils.keyboards import main_menu_keyboard


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🍇 <b>Журнал виноградника</b>\n\nВыбери раздел:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )


async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Главное меню:",
        reply_markup=main_menu_keyboard(),
    )


async def cb_main_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🍇 <b>Журнал виноградника</b>\n\nВыбери раздел:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )


async def cb_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer("Отменено")
    ctx.user_data.clear()
    await q.edit_message_text(
        "Главное меню:",
        reply_markup=main_menu_keyboard(),
    )
