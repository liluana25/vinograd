"""Main menu and shared navigation."""
from __future__ import annotations

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from bot.utils.keyboards import main_menu_keyboard

# Persistent bottom keyboard shown once on /start
_BOTTOM_KB = ReplyKeyboardMarkup(
    [["/menu"]],
    resize_keyboard=True,
    is_persistent=True,
)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🍇 <b>Журнал виноградника</b>\n\n"
        "Кнопка /menu закреплена внизу — возвращает сюда из любого места.",
        reply_markup=_BOTTOM_KB,
        parse_mode="HTML",
    )
    await update.message.reply_text(
        "Выбери раздел:",
        reply_markup=main_menu_keyboard(),
    )


async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🍇 <b>Журнал виноградника</b>\n\nВыбери раздел:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )


async def cmd_menu_to_main(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    """Conversation fallback: cancel any active flow and return to main menu."""
    ctx.user_data.clear()
    await update.message.reply_text(
        "🍇 <b>Журнал виноградника</b>\n\nВыбери раздел:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )
    return ConversationHandler.END


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
