"""Variety management: list, add, rename, notes."""
from __future__ import annotations

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters

from bot.database import queries as db
from bot.utils.fuzzy import fuzzy_find_variety
from bot.utils.keyboards import varieties_menu_keyboard, back_keyboard, varieties_keyboard

# Conversation states
VAR_WAITING_NAME = "var_waiting_name"
VAR_WAITING_RENAME_PICK = "var_waiting_rename_pick"
VAR_WAITING_NEW_NAME = "var_waiting_new_name"
VAR_WAITING_NOTE_PICK = "var_waiting_note_pick"
VAR_WAITING_NOTE_TEXT = "var_waiting_note_text"


async def show_varieties_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("🌿 <b>Мои сорта</b>", reply_markup=varieties_menu_keyboard(), parse_mode="HTML")


async def cb_varieties_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    varieties = await db.get_all_varieties()
    if not varieties:
        await q.edit_message_text("Сортов пока нет. Добавь первый!", reply_markup=back_keyboard("menu:varieties"))
        return
    lines = [f"🌿 <b>Мои сорта ({len(varieties)})</b>\n"]
    for v in varieties:
        lines.append(f"• <b>{v['name']}</b>")
        if v.get("notes"):
            lines.append(f"  <i>{v['notes']}</i>")
    await q.edit_message_text(
        "\n".join(lines),
        reply_markup=back_keyboard("menu:varieties"),
        parse_mode="HTML",
    )


async def cb_variety_add_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    ctx.user_data["var_action"] = "add"
    await q.edit_message_text(
        "Введи название нового сорта:\n(или /cancel для отмены)",
        reply_markup=None,
    )
    return VAR_WAITING_NAME


async def receive_variety_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    existing = await db.get_all_varieties()
    direct, suggestions = fuzzy_find_variety(name, existing)

    if direct:
        await update.message.reply_text(
            f"Сорт <b>{direct['name']}</b> уже есть в списке.",
            reply_markup=back_keyboard("menu:varieties"),
            parse_mode="HTML",
        )
        return ConversationHandler.END

    if suggestions:
        ctx.user_data["pending_variety_name"] = name
        buttons = [
            [InlineKeyboardButton(s["name"], callback_data=f"var_exist:{s['id']}")]
            for s in suggestions
        ]
        buttons.append([InlineKeyboardButton("➕ Добавить как новый", callback_data="var_exist:new")])
        buttons.append([InlineKeyboardButton("« Отмена", callback_data="menu:cancel")])
        await update.message.reply_text(
            f"Похожие сорта уже есть:\n\nДобавить как новый «{name}» или выбрать существующий?",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="HTML",
        )
        return VAR_WAITING_NAME

    await db.add_variety(name)
    await update.message.reply_text(
        f"✅ Сорт <b>{name}</b> добавлен!",
        reply_markup=back_keyboard("menu:varieties"),
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def cb_variety_exists_choice(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    choice = q.data.split(":")[1]
    if choice == "new":
        name = ctx.user_data.pop("pending_variety_name", "")
        await db.add_variety(name)
        await q.edit_message_text(
            f"✅ Сорт <b>{name}</b> добавлен!",
            reply_markup=back_keyboard("menu:varieties"),
            parse_mode="HTML",
        )
    else:
        variety = await db.get_variety_by_id(int(choice))
        await q.edit_message_text(
            f"Хорошо, используем <b>{variety['name']}</b>.",
            reply_markup=back_keyboard("menu:varieties"),
            parse_mode="HTML",
        )
    return ConversationHandler.END


async def cb_variety_rename_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    varieties = await db.get_all_varieties()
    if not varieties:
        await q.edit_message_text("Нет сортов для переименования.", reply_markup=back_keyboard("menu:varieties"))
        return ConversationHandler.END
    await q.edit_message_text(
        "Выбери сорт для переименования:",
        reply_markup=varieties_keyboard(varieties, callback_prefix="var_rename"),
    )
    return VAR_WAITING_RENAME_PICK


async def cb_variety_rename_pick(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    vid = int(q.data.split(":")[1])
    variety = await db.get_variety_by_id(vid)
    ctx.user_data["rename_variety_id"] = vid
    ctx.user_data["rename_variety_old"] = variety["name"]
    await q.edit_message_text(
        f"Переименовываем <b>{variety['name']}</b>.\n\nВведи новое название:",
        parse_mode="HTML",
    )
    return VAR_WAITING_NEW_NAME


async def receive_new_variety_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    new_name = update.message.text.strip()
    vid = ctx.user_data.pop("rename_variety_id")
    old_name = ctx.user_data.pop("rename_variety_old", "")
    await db.rename_variety(vid, new_name)
    await update.message.reply_text(
        f"✅ Сорт переименован: <b>{old_name}</b> → <b>{new_name}</b>",
        reply_markup=back_keyboard("menu:varieties"),
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def cb_variety_note_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    varieties = await db.get_all_varieties()
    if not varieties:
        await q.edit_message_text("Нет сортов.", reply_markup=back_keyboard("menu:varieties"))
        return ConversationHandler.END
    await q.edit_message_text(
        "Выбери сорт для заметки:",
        reply_markup=varieties_keyboard(varieties, callback_prefix="var_note"),
    )
    return VAR_WAITING_NOTE_PICK


async def cb_variety_note_pick(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> str:
    q = update.callback_query
    await q.answer()
    vid = int(q.data.split(":")[1])
    variety = await db.get_variety_by_id(vid)
    ctx.user_data["note_variety_id"] = vid
    current = variety.get("notes") or "пусто"
    await q.edit_message_text(
        f"Сорт: <b>{variety['name']}</b>\nТекущая заметка: <i>{current}</i>\n\nВведи новую заметку:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("« Отмена", callback_data="menu:cancel"),
        ]]),
        parse_mode="HTML",
    )
    return VAR_WAITING_NOTE_TEXT


async def receive_variety_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    vid = ctx.user_data.pop("note_variety_id")
    note = update.message.text.strip()
    await db.update_variety_notes(vid, note)
    await update.message.reply_text(
        "✅ Заметка сохранена.",
        reply_markup=back_keyboard("menu:varieties"),
    )
    return ConversationHandler.END


async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data.clear()
    await update.message.reply_text("Отменено.", reply_markup=back_keyboard("menu:main"))
    return ConversationHandler.END
