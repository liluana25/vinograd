"""Backup command — sends the SQLite database file."""
from __future__ import annotations

import os
from datetime import date as Date

from telegram import Update
from telegram.ext import ContextTypes

from bot.config import DB_PATH


async def cmd_backup(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
        send_msg = update.callback_query.message
    else:
        send_msg = update.message

    if not os.path.exists(DB_PATH):
        await send_msg.reply_text("База данных не найдена.")
        return

    filename = f"vineyard_{Date.today().isoformat()}.db"
    await send_msg.reply_document(
        document=open(DB_PATH, "rb"),
        filename=filename,
        caption=f"💾 Резервная копия базы данных на {Date.today().isoformat()}",
    )
