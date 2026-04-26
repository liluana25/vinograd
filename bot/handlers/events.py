"""Event logging flow."""
from __future__ import annotations

from datetime import date as Date

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from bot.database import queries as db
from bot.utils.fuzzy import fuzzy_find_variety, fuzzy_find_product
from bot.utils.keyboards import (
    event_type_keyboard, skip_cancel_keyboard, back_keyboard,
    products_keyboard, varieties_keyboard,
)
from bot.utils.keyboards import EVENT_TYPES

# States
EV_VARIETY = "ev_variety"
EV_TYPE    = "ev_type"
EV_DATE    = "ev_date"
EV_PRODUCT = "ev_product"
EV_PRODUCT_NEW_NAME = "ev_product_new_name"
EV_WEIGHT  = "ev_weight"
EV_NOTE    = "ev_note"
EV_PHOTO   = "ev_photo"

NEEDS_PRODUCT = {"treatment", "fertilizing"}
NEEDS_WEIGHT  = {"harvest"}


async def start_event(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    ctx.user_data.clear()
    ctx.user_data["ev_flow"] = True
    varieties = await db.get_all_varieties()
    if not varieties:
        await q.edit_message_text(
            "У тебя пока нет сортов. Сначала добавь сорт в разделе «Мои сорта».",
            reply_markup=back_keyboard("menu:main"),
        )
        return ConversationHandler.END
    await q.edit_message_text(
        "Выбери сорт (или напиши название):",
        reply_markup=varieties_keyboard(varieties, callback_prefix="ev_var"),
    )
    return EV_VARIETY


async def cb_ev_variety(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    vid = int(q.data.split(":")[1])
    return await _set_variety_and_ask_type(vid, update, ctx)


async def text_ev_variety(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    query = update.message.text.strip()
    varieties = await db.get_all_varieties()
    direct, suggestions = fuzzy_find_variety(query, varieties)

    if direct:
        return await _set_variety_and_ask_type(direct["id"], update, ctx)

    if suggestions:
        buttons = [
            [InlineKeyboardButton(s["name"], callback_data=f"ev_var:{s['id']}")]
            for s in suggestions
        ]
        buttons.append([InlineKeyboardButton("« Отмена", callback_data="menu:cancel")])
        await update.message.reply_text(
            f"Не нашла точного совпадения для «{query}». Возможно, имелось в виду:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return EV_VARIETY

    await update.message.reply_text(
        f"Сорт «{query}» не найден. Добавь его в разделе «Мои сорта».",
        reply_markup=back_keyboard("menu:main"),
    )
    return ConversationHandler.END


async def _set_variety_and_ask_type(vid: int, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    ctx.user_data["ev_variety_id"] = vid
    variety = await db.get_variety_by_id(vid)
    ctx.user_data["ev_variety_name"] = variety["name"]
    text = f"Сорт: <b>{variety['name']}</b>\n\nВыбери тип события:"
    kb = event_type_keyboard()
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")
    return EV_TYPE


async def cb_ev_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    etype = q.data.split(":")[1]
    ctx.user_data["ev_type"] = etype
    today = Date.today().isoformat()
    await q.edit_message_text(
        f"Событие: <b>{EVENT_TYPES[etype]}</b>\n\n"
        f"Введи дату (ГГГГ-ММ-ДД) или нажми «Сегодня»:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"Сегодня ({today})", callback_data=f"ev_date:{today}"),
            InlineKeyboardButton("« Отмена", callback_data="menu:cancel"),
        ]]),
        parse_mode="HTML",
    )
    return EV_DATE


async def cb_ev_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    date_str = q.data.split(":")[1]
    ctx.user_data["ev_date"] = date_str
    return await _after_date(update, ctx)


async def text_ev_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    text = update.message.text.strip()
    try:
        Date.fromisoformat(text)
    except ValueError:
        await update.message.reply_text(
            "Неверный формат. Введи дату в формате ГГГГ-ММ-ДД, например 2024-06-15:"
        )
        return EV_DATE
    ctx.user_data["ev_date"] = text
    return await _after_date(update, ctx)


async def _after_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    etype = ctx.user_data["ev_type"]
    if etype in NEEDS_PRODUCT:
        category = "treatment" if etype == "treatment" else "fertilizing"
        products = await db.get_all_products(category)
        if products:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    "Выбери препарат/удобрение или добавь новый:",
                    reply_markup=products_keyboard(products, callback_prefix="ev_prod"),
                )
            else:
                await update.message.reply_text(
                    "Выбери препарат/удобрение или введи название:",
                    reply_markup=products_keyboard(products, callback_prefix="ev_prod"),
                )
        else:
            msg = "Введи название препарата/удобрения:"
            if update.callback_query:
                await update.callback_query.edit_message_text(msg)
            else:
                await update.message.reply_text(msg)
        return EV_PRODUCT
    elif etype in NEEDS_WEIGHT:
        msg = "Введи вес урожая в кг (например: 2.5):"
        if update.callback_query:
            await update.callback_query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return EV_WEIGHT
    else:
        return await _ask_note(update, ctx)


async def cb_ev_product(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    val = q.data.split(":")[1]
    if val == "new":
        await q.edit_message_text("Введи название нового препарата/удобрения:")
        return EV_PRODUCT_NEW_NAME
    ctx.user_data["ev_product_id"] = int(val)
    return await _ask_note(update, ctx)


async def text_ev_product(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    text = update.message.text.strip()
    etype = ctx.user_data["ev_type"]
    category = "treatment" if etype == "treatment" else "fertilizing"
    products = await db.get_all_products(category)
    direct, suggestions = fuzzy_find_product(text, products)

    if direct:
        ctx.user_data["ev_product_id"] = direct["id"]
        return await _ask_note(update, ctx)

    if suggestions:
        buttons = [
            [InlineKeyboardButton(s["name"], callback_data=f"ev_prod:{s['id']}")]
            for s in suggestions
        ]
        buttons.append([InlineKeyboardButton("➕ Добавить новый", callback_data="ev_prod:new")])
        buttons.append([InlineKeyboardButton("« Отмена", callback_data="menu:cancel")])
        await update.message.reply_text(
            f"Похожие препараты найдены. Выбери или добавь новый «{text}»:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        ctx.user_data["ev_product_new_name"] = text
        return EV_PRODUCT

    pid = await db.add_product(text, category)
    ctx.user_data["ev_product_id"] = pid
    return await _ask_note(update, ctx)


async def receive_new_product_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    name = update.message.text.strip()
    etype = ctx.user_data["ev_type"]
    category = "treatment" if etype == "treatment" else "fertilizing"
    pid = await db.add_product(name, category)
    ctx.user_data["ev_product_id"] = pid
    return await _ask_note(update, ctx)


async def text_ev_weight(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    text = update.message.text.strip().replace(",", ".")
    try:
        weight = float(text)
    except ValueError:
        await update.message.reply_text("Введи число, например 2.5:")
        return EV_WEIGHT
    ctx.user_data["ev_weight"] = weight
    return await _ask_note(update, ctx)


async def _ask_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    kb = skip_cancel_keyboard(skip_data="ev_skip_note")
    msg = "Добавить заметку? (введи текст или пропусти):"
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=kb)
    else:
        await update.message.reply_text(msg, reply_markup=kb)
    return EV_NOTE


async def cb_ev_skip_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    ctx.user_data["ev_note"] = None
    return await _ask_photo(update, ctx)


async def text_ev_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    ctx.user_data["ev_note"] = update.message.text.strip()
    return await _ask_photo(update, ctx)


async def _ask_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    kb = skip_cancel_keyboard(skip_data="ev_skip_photo")
    msg = "Прикрепить фото? Отправь фото или пропусти:"
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=kb)
    else:
        await update.message.reply_text(msg, reply_markup=kb)
    return EV_PHOTO


async def cb_ev_skip_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    ctx.user_data["ev_photo"] = None
    return await _save_event(update, ctx)


async def receive_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    photo = update.message.photo[-1]
    ctx.user_data["ev_photo"] = photo.file_id
    return await _save_event(update, ctx)


async def _save_event(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ud = ctx.user_data
    await db.add_event(
        variety_id=ud["ev_variety_id"],
        event_type=ud["ev_type"],
        date=ud["ev_date"],
        weight_kg=ud.get("ev_weight"),
        product_id=ud.get("ev_product_id"),
        note=ud.get("ev_note"),
        photo_file_id=ud.get("ev_photo"),
    )
    etype_label = EVENT_TYPES[ud["ev_type"]]
    text = (
        f"✅ Сохранено!\n\n"
        f"<b>{ud['ev_variety_name']}</b>\n"
        f"{etype_label}  —  {ud['ev_date']}"
    )
    if ud.get("ev_note"):
        text += f"\n{ud['ev_note']}"
    ctx.user_data.clear()
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=back_keyboard("menu:main"), parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            text, reply_markup=back_keyboard("menu:main"), parse_mode="HTML"
        )
    return ConversationHandler.END


async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data.clear()
    await update.message.reply_text("Отменено.", reply_markup=back_keyboard("menu:main"))
    return ConversationHandler.END
