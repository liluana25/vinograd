"""Procedure templates: create, apply, delete."""
from __future__ import annotations

from datetime import date as Date

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from bot.database import queries as db
from bot.utils.keyboards import (
    templates_menu_keyboard, back_keyboard, event_type_keyboard,
    products_keyboard, skip_cancel_keyboard, varieties_multiselect_keyboard,
)
from bot.utils.keyboards import EVENT_TYPES
from bot.utils.formatters import fmt_date

# States
TPL_NEW_NAME        = "tpl_new_name"
TPL_NEW_TYPE        = "tpl_new_type"
TPL_NEW_PRODUCT     = "tpl_new_product"
TPL_NEW_PRODUCT_NEW = "tpl_new_product_new"
TPL_NEW_NOTE        = "tpl_new_note"

TPL_APPLY_PICK     = "tpl_apply_pick"
TPL_APPLY_SEL      = "tpl_apply_sel"
TPL_APPLY_DATE     = "tpl_apply_date"
TPL_APPLY_NOTE     = "tpl_apply_note"
TPL_APPLY_PROD     = "tpl_apply_prod"
TPL_APPLY_PROD_NEW = "tpl_apply_prod_new"

TPL_DELETE_PICK = "tpl_delete_pick"

NEEDS_PRODUCT = {"treatment", "fertilizing"}


async def show_templates_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("🗂 <b>Шаблоны</b>", reply_markup=templates_menu_keyboard(), parse_mode="HTML")


# ── Create template ───────────────────────────────────────────────────────────

async def cb_tpl_new_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    ctx.user_data.clear()
    await q.edit_message_text("Введи название шаблона (например «Весенняя обработка»):")
    return TPL_NEW_NAME


async def text_tpl_new_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    name = update.message.text.strip()
    ctx.user_data["tpl_name"] = name
    await update.message.reply_text(
        f"Шаблон: <b>{name}</b>\n\n"
        "Выбери <b>тип операции</b>, которую выполняет этот шаблон.\n"
        "Например: «Весенняя обработка» = <b>💊 Обработка</b>; «Летний полив» = <b>💧 Полив</b>:",
        reply_markup=event_type_keyboard(),
        parse_mode="HTML",
    )
    return TPL_NEW_TYPE


async def cb_tpl_new_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    etype = q.data.split(":")[1]
    ctx.user_data["tpl_type"] = etype
    if etype in NEEDS_PRODUCT:
        category = "treatment" if etype == "treatment" else "fertilizing"
        products = await db.get_all_products(category)
        if products:
            await q.edit_message_text(
                "Выбери препарат по умолчанию (можно будет изменить при применении):",
                reply_markup=products_keyboard(products, "tpl_prod"),
            )
            return TPL_NEW_PRODUCT
        else:
            await q.edit_message_text("Введи название препарата по умолчанию:")
            return TPL_NEW_PRODUCT_NEW
    return await _ask_tpl_note(update, ctx)


async def cb_tpl_new_product(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    val = q.data.split(":")[1]
    if val == "new":
        await q.edit_message_text("Введи название нового препарата:")
        return TPL_NEW_PRODUCT_NEW
    ctx.user_data["tpl_product_id"] = int(val)
    return await _ask_tpl_note(update, ctx)


async def receive_tpl_new_product(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    name = update.message.text.strip()
    etype = ctx.user_data["tpl_type"]
    category = "treatment" if etype == "treatment" else "fertilizing"
    pid = await db.add_product(name, category)
    ctx.user_data["tpl_product_id"] = pid
    return await _ask_tpl_note(update, ctx)


async def _ask_tpl_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    msg = "Заметка по умолчанию (необязательно):"
    kb = skip_cancel_keyboard("tpl_skip_note")
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=kb)
    else:
        await update.message.reply_text(msg, reply_markup=kb)
    return TPL_NEW_NOTE


async def cb_tpl_skip_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    ctx.user_data["tpl_note"] = None
    return await _save_template(update, ctx)


async def text_tpl_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["tpl_note"] = update.message.text.strip()
    return await _save_template(update, ctx)


async def _save_template(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ud = ctx.user_data
    await db.add_template(
        name=ud["tpl_name"],
        event_type=ud["tpl_type"],
        default_product_id=ud.get("tpl_product_id"),
        default_note=ud.get("tpl_note") or "",
    )
    text = f"✅ Шаблон <b>{ud['tpl_name']}</b> создан!"
    ctx.user_data.clear()
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=back_keyboard("menu:templates"), parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=back_keyboard("menu:templates"), parse_mode="HTML")
    return ConversationHandler.END


# ── Apply template ────────────────────────────────────────────────────────────

async def cb_tpl_apply_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    templates = await db.get_all_templates()
    if not templates:
        await q.edit_message_text("Шаблонов нет. Создай первый!", reply_markup=back_keyboard("menu:templates"))
        return ConversationHandler.END
    ctx.user_data.clear()
    buttons = [[InlineKeyboardButton(t["name"], callback_data=f"tpl_pick:{t['id']}")] for t in templates]
    buttons.append([InlineKeyboardButton("« Назад", callback_data="menu:templates")])
    await q.edit_message_text("Выбери шаблон:", reply_markup=InlineKeyboardMarkup(buttons))
    return TPL_APPLY_PICK


async def cb_tpl_apply_pick(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    tid = int(q.data.split(":")[1])
    template = await db.get_template_by_id(tid)
    ctx.user_data["apply_tpl"] = template
    ctx.user_data["apply_selected"] = set()
    varieties = await db.get_all_varieties()
    ctx.user_data["apply_varieties"] = varieties
    await q.edit_message_text(
        f"Шаблон: <b>{template['name']}</b>\n\nОтметь кусты:",
        reply_markup=varieties_multiselect_keyboard(varieties, set()),
        parse_mode="HTML",
    )
    return TPL_APPLY_SEL


async def cb_tpl_sel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    val = q.data.split(":")[1]
    varieties = ctx.user_data["apply_varieties"]
    selected: set[int] = ctx.user_data["apply_selected"]

    if val == "all":
        selected = {v["id"] for v in varieties}
    elif val == "none":
        selected = set()
    elif val == "confirm":
        if not selected:
            await q.answer("Выбери хотя бы один куст", show_alert=True)
            return TPL_APPLY_SEL
        ctx.user_data["apply_selected"] = selected
        today = Date.today().isoformat()
        await q.edit_message_text(
            "Дата (ГГГГ-ММ-ДД):",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f"Сегодня ({today})", callback_data=f"tpl_date:{today}"),
            ]]),
        )
        return TPL_APPLY_DATE
    else:
        vid = int(val)
        if vid in selected:
            selected.discard(vid)
        else:
            selected.add(vid)

    ctx.user_data["apply_selected"] = selected
    await q.edit_message_reply_markup(
        reply_markup=varieties_multiselect_keyboard(varieties, selected)
    )
    return TPL_APPLY_SEL


async def cb_tpl_apply_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    ctx.user_data["apply_date"] = q.data.split(":")[1]
    return await _after_tpl_date(update, ctx)


async def text_tpl_apply_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    text = update.message.text.strip()
    try:
        Date.fromisoformat(text)
    except ValueError:
        await update.message.reply_text("Неверный формат. ГГГГ-ММ-ДД:")
        return TPL_APPLY_DATE
    ctx.user_data["apply_date"] = text
    return await _after_tpl_date(update, ctx)


async def _after_tpl_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    tpl = ctx.user_data["apply_tpl"]
    etype = tpl["event_type"]
    if etype in NEEDS_PRODUCT:
        category = "treatment" if etype == "treatment" else "fertilizing"
        products = await db.get_all_products(category)
        default_pid = tpl.get("default_product_id")
        if default_pid:
            ctx.user_data["apply_product_id"] = default_pid
            pname = tpl.get("product_name") or ""
            msg = f"Препарат: <b>{pname}</b>. Использовать этот?"
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Да", callback_data="tpl_use_default_prod"),
                InlineKeyboardButton("Другой", callback_data="tpl_change_prod"),
            ]])
            if update.callback_query:
                await update.callback_query.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")
            else:
                await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")
            return TPL_APPLY_PROD
        elif products:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    "Выбери препарат:", reply_markup=products_keyboard(products, "tpl_ap_prod")
                )
            else:
                await update.message.reply_text(
                    "Выбери препарат:", reply_markup=products_keyboard(products, "tpl_ap_prod")
                )
            return TPL_APPLY_PROD
        else:
            if update.callback_query:
                await update.callback_query.edit_message_text("Введи название препарата:")
            else:
                await update.message.reply_text("Введи название препарата:")
            return TPL_APPLY_PROD_NEW
    return await _ask_tpl_apply_note(update, ctx)


async def cb_tpl_use_default_prod(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    return await _ask_tpl_apply_note(update, ctx)


async def cb_tpl_change_prod(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    tpl = ctx.user_data["apply_tpl"]
    category = "treatment" if tpl["event_type"] == "treatment" else "fertilizing"
    products = await db.get_all_products(category)
    await q.edit_message_text("Выбери препарат:", reply_markup=products_keyboard(products, "tpl_ap_prod"))
    return TPL_APPLY_PROD


async def cb_tpl_ap_prod(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    val = q.data.split(":")[1]
    if val == "new":
        await q.edit_message_text("Введи название нового препарата:")
        return TPL_APPLY_PROD_NEW
    ctx.user_data["apply_product_id"] = int(val)
    return await _ask_tpl_apply_note(update, ctx)


async def receive_tpl_ap_prod_new(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    name = update.message.text.strip()
    tpl = ctx.user_data["apply_tpl"]
    category = "treatment" if tpl["event_type"] == "treatment" else "fertilizing"
    pid = await db.add_product(name, category)
    ctx.user_data["apply_product_id"] = pid
    return await _ask_tpl_apply_note(update, ctx)


async def _ask_tpl_apply_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    tpl = ctx.user_data["apply_tpl"]
    default_note = tpl.get("default_note") or ""
    if default_note:
        msg = f"Заметка по умолчанию: <i>{default_note}</i>\nИспользовать или введи свою:"
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Использовать", callback_data="tpl_use_default_note"),
            InlineKeyboardButton("Пропустить",      callback_data="tpl_skip_note"),
        ]])
    else:
        msg = "Добавить заметку? (введи или пропусти):"
        kb = skip_cancel_keyboard("tpl_skip_note")
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=kb, parse_mode="HTML")
    else:
        await update.message.reply_text(msg, reply_markup=kb, parse_mode="HTML")
    return TPL_APPLY_NOTE


async def cb_tpl_use_default_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    ctx.user_data["apply_note"] = ctx.user_data["apply_tpl"].get("default_note")
    return await _apply_template_to_varieties(update, ctx)


async def cb_tpl_skip_note_apply(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    ctx.user_data["apply_note"] = None
    return await _apply_template_to_varieties(update, ctx)


async def text_tpl_apply_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data["apply_note"] = update.message.text.strip()
    return await _apply_template_to_varieties(update, ctx)


async def _apply_template_to_varieties(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ud = ctx.user_data
    tpl      = ud["apply_tpl"]
    selected = ud["apply_selected"]
    date_str = ud["apply_date"]
    note     = ud.get("apply_note")
    prod_id  = ud.get("apply_product_id")

    count = 0
    for vid in selected:
        await db.add_event(
            variety_id=vid,
            event_type=tpl["event_type"],
            date=date_str,
            product_id=prod_id,
            note=note,
        )
        count += 1

    text = (
        f"✅ Шаблон <b>{tpl['name']}</b> применён!\n"
        f"Событий создано: {count} ({fmt_date(date_str)})"
    )
    ctx.user_data.clear()
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=back_keyboard("menu:main"), parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=back_keyboard("menu:main"), parse_mode="HTML")
    return ConversationHandler.END


# ── Delete template ───────────────────────────────────────────────────────────

async def cb_tpl_delete_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    templates = await db.get_all_templates()
    if not templates:
        await q.edit_message_text("Нет шаблонов.", reply_markup=back_keyboard("menu:templates"))
        return ConversationHandler.END
    buttons = [[InlineKeyboardButton(t["name"], callback_data=f"tpl_del_pick:{t['id']}")] for t in templates]
    buttons.append([InlineKeyboardButton("« Назад", callback_data="menu:templates")])
    await q.edit_message_text("Выбери шаблон для удаления:", reply_markup=InlineKeyboardMarkup(buttons))
    return TPL_DELETE_PICK


async def cb_tpl_delete_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    tid = int(q.data.split(":")[1])
    tpl = await db.get_template_by_id(tid)
    await db.delete_template(tid)
    await q.edit_message_text(
        f"🗑 Шаблон <b>{tpl['name']}</b> удалён.",
        reply_markup=back_keyboard("menu:templates"),
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data.clear()
    await update.message.reply_text("Отменено.", reply_markup=back_keyboard("menu:main"))
    return ConversationHandler.END
