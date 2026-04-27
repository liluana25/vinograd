"""Cuttings module."""
from __future__ import annotations

import logging
from datetime import date as Date

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

logger = logging.getLogger(__name__)

from bot.database import queries as db
from bot.utils.keyboards import (
    cuttings_menu_keyboard, back_keyboard, varieties_keyboard, skip_cancel_keyboard,
)
from bot.utils.formatters import fmt_cutting_card, fmt_cuttings_stats

# States
CUT_VARIETY    = "cut_variety"
CUT_DATE       = "cut_date"
CUT_COUNT      = "cut_count"
CUT_STORAGE    = "cut_storage"
CUT_PICK       = "cut_pick"
CUT_EDIT_FIELD = "cut_edit_field"
CUT_EDIT_VALUE = "cut_edit_value"


async def show_cuttings_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("✂️ <b>Черенки</b>", reply_markup=cuttings_menu_keyboard(), parse_mode="HTML")


async def cb_cut_new_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    ctx.user_data.clear()
    varieties = await db.get_all_varieties()
    if not varieties:
        await q.edit_message_text("Нет сортов. Добавь сорт в разделе «Мои сорта».", reply_markup=back_keyboard("menu:cuttings"))
        return ConversationHandler.END
    await q.edit_message_text("Выбери сорт-родитель:", reply_markup=varieties_keyboard(varieties, "cut_var"))
    return CUT_VARIETY


async def cb_cut_variety(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    vid = int(q.data.split(":")[1])
    variety = await db.get_variety_by_id(vid)
    ctx.user_data["cut_variety_id"] = vid
    ctx.user_data["cut_variety_name"] = variety["name"]
    today = Date.today().isoformat()
    await q.edit_message_text(
        f"Сорт: <b>{variety['name']}</b>\n\nДата нарезки (ГГГГ-ММ-ДД):",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"Сегодня ({today})", callback_data=f"cut_date:{today}"),
        ]]),
        parse_mode="HTML",
    )
    return CUT_DATE


async def cb_cut_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    ctx.user_data["cut_date"] = q.data.split(":")[1]
    await q.edit_message_text("Сколько черенков нарезано? (введи число):")
    return CUT_COUNT


async def text_cut_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    text = update.message.text.strip()
    try:
        Date.fromisoformat(text)
    except ValueError:
        await update.message.reply_text("Неверный формат. Введи дату ГГГГ-ММ-ДД:")
        return CUT_DATE
    ctx.user_data["cut_date"] = text
    await update.message.reply_text("Сколько черенков нарезано? (введи число):")
    return CUT_COUNT


async def text_cut_count(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    try:
        ctx.user_data["cut_count"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Введи целое число:")
        return CUT_COUNT
    await update.message.reply_text(
        "Условия хранения (напр. «подвал, влажный песок») или пропусти:",
        reply_markup=skip_cancel_keyboard("cut_skip_storage"),
    )
    return CUT_STORAGE


async def cb_cut_skip_storage(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    ctx.user_data["cut_storage"] = None
    return await _save_cutting(update, ctx)


async def text_cut_storage(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["cut_storage"] = update.message.text.strip()
    return await _save_cutting(update, ctx)


async def _save_cutting(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ud = ctx.user_data
    # Extract values before clear so they survive it
    variety_id   = ud.get("cut_variety_id")
    variety_name = ud.get("cut_variety_name", "?")
    cut_date     = ud.get("cut_date", "")
    cut_count    = ud.get("cut_count", 0)
    storage      = ud.get("cut_storage") or ""

    try:
        season = int(cut_date[:4])
        cid = await db.add_cutting(
            variety_id=variety_id,
            season=season,
            cut_date=cut_date,
            cut_count=cut_count,
            storage_notes=storage,
        )
    except Exception:
        logger.exception("Failed to save cutting")
        target = update.message or (update.callback_query.message if update.callback_query else None)
        if target:
            await target.reply_text("❌ Ошибка сохранения. Попробуй ещё раз или нажми /cancel")
        ctx.user_data.clear()
        return ConversationHandler.END

    text = f"✅ Партия черенков сохранена!\n\n<b>{variety_name}</b>, {cut_count} шт., {cut_date}"
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Обновить этапы", callback_data=f"cut_edit:{cid}")],
        [InlineKeyboardButton("« Черенки", callback_data="menu:cuttings")],
    ])
    ctx.user_data.clear()
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=buttons, parse_mode="HTML")
        else:
            await update.message.reply_text(text, reply_markup=buttons, parse_mode="HTML")
    except Exception:
        logger.exception("Failed to send cutting confirmation")
        target = update.message or (update.callback_query.message if update.callback_query else None)
        if target:
            await target.reply_text("✅ Черенки сохранены (но не могу показать детали).")
    return ConversationHandler.END


# ── List cuttings ─────────────────────────────────────────────────────────────

async def cb_cut_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    varieties = await db.get_all_varieties()
    if not varieties:
        await q.edit_message_text("Нет данных.", reply_markup=back_keyboard("menu:cuttings"))
        return ConversationHandler.END
    await q.edit_message_text(
        "Выбери сорт для просмотра черенков:",
        reply_markup=varieties_keyboard(varieties, "cut_list_var"),
    )
    return CUT_PICK


async def cb_cut_list_variety(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    vid = int(q.data.split(":")[1])
    cuttings = await db.get_cuttings_by_variety(vid)
    if not cuttings:
        await q.edit_message_text("Нет черенков для этого сорта.", reply_markup=back_keyboard("menu:cuttings"))
        return ConversationHandler.END
    buttons = [
        [InlineKeyboardButton(
            f"{c['cut_date'] or '?'}  {c['cut_count']} шт.",
            callback_data=f"cut_view:{c['id']}"
        )]
        for c in cuttings
    ]
    buttons.append([InlineKeyboardButton("« Назад", callback_data="menu:cuttings")])
    await q.edit_message_text("Партии черенков:", reply_markup=InlineKeyboardMarkup(buttons))
    return ConversationHandler.END


async def cb_cut_view(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    cid = int(q.data.split(":")[1])
    c = await db.get_cutting_by_id(cid)
    text = fmt_cutting_card(c)
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Обновить", callback_data=f"cut_edit:{cid}")],
        [InlineKeyboardButton("🗑 Удалить",  callback_data=f"cut_del:{cid}")],
        [InlineKeyboardButton("« Назад",     callback_data="menu:cuttings")],
    ])
    await q.edit_message_text(text, reply_markup=buttons, parse_mode="HTML")


# ── Edit cutting ──────────────────────────────────────────────────────────────

EDIT_FIELDS = {
    "rooting_count":  "На укоренение (кол-во)",
    "rooted_count":   "Прижилось (кол-во)",
    "potted_count":   "В ёмкости (кол-во)",
    "sold_count":     "Продано (кол-во)",
    "sold_to":        "Кому продано",
    "planted_count":  "Высажено в грунт (кол-во)",
    "notes":          "Заметки",
}


async def cb_cut_edit(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    cid = int(q.data.split(":")[1])
    ctx.user_data["cut_edit_id"] = cid
    buttons = [
        [InlineKeyboardButton(label, callback_data=f"cut_ef:{field}")]
        for field, label in EDIT_FIELDS.items()
    ]
    buttons.append([InlineKeyboardButton("« Назад", callback_data="menu:cuttings")])
    await q.edit_message_text("Что обновить?", reply_markup=InlineKeyboardMarkup(buttons))
    return CUT_EDIT_FIELD


async def cb_cut_edit_field(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    field = q.data.split(":")[1]
    ctx.user_data["cut_edit_field"] = field
    label = EDIT_FIELDS[field]
    await q.edit_message_text(f"Введи значение для «{label}»:")
    return CUT_EDIT_VALUE


async def text_cut_edit_value(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    field = ctx.user_data.pop("cut_edit_field")
    cid   = ctx.user_data.pop("cut_edit_id")
    value_str = update.message.text.strip()

    int_fields = {"rooting_count","rooted_count","potted_count","sold_count","planted_count"}
    if field in int_fields:
        try:
            value = int(value_str)
        except ValueError:
            await update.message.reply_text("Введи целое число:")
            ctx.user_data["cut_edit_field"] = field
            ctx.user_data["cut_edit_id"] = cid
            return CUT_EDIT_VALUE
    else:
        value = value_str

    await db.update_cutting(cid, **{field: value})
    cutting = await db.get_cutting_by_id(cid)
    await update.message.reply_text(
        "✅ Обновлено!\n\n" + fmt_cutting_card(cutting),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Ещё раз", callback_data=f"cut_edit:{cid}")],
            [InlineKeyboardButton("« Черенки",  callback_data="menu:cuttings")],
        ]),
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def cb_cut_delete(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    cid = int(q.data.split(":")[1])
    await db.delete_cutting(cid)
    await q.edit_message_text("🗑 Партия удалена.", reply_markup=back_keyboard("menu:cuttings"))


# ── Stats ─────────────────────────────────────────────────────────────────────

async def cb_cut_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    year = Date.today().year
    rows = await db.get_cuttings_stats(year)
    await q.edit_message_text(
        fmt_cuttings_stats(year, rows),
        reply_markup=back_keyboard("menu:cuttings"),
        parse_mode="HTML",
    )


async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data.clear()
    await update.message.reply_text("Отменено.", reply_markup=back_keyboard("menu:main"))
    return ConversationHandler.END
