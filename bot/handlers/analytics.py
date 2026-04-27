"""Analytics handlers."""
from __future__ import annotations

from datetime import date as Date

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.database import queries as db
from bot.utils.keyboards import (
    analytics_menu_keyboard, back_keyboard, varieties_keyboard,
    years_keyboard, months_keyboard,
)
from bot.utils.formatters import (
    fmt_calendar, fmt_variety_history, fmt_harvest,
    fmt_phenology, fmt_treatments, fmt_products_usage,
    fmt_cuttings_stats,
)


async def show_analytics_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "📊 <b>Аналитика</b>", reply_markup=analytics_menu_keyboard(), parse_mode="HTML"
    )


def _current_years() -> list[int]:
    current = Date.today().year
    return list(range(current, current - 5, -1))


def _calendar_years() -> list[int]:
    """Calendar goes back to 2019 to cover full vineyard history."""
    current = Date.today().year
    return list(range(current, 2019, -1))


# ── Calendar ──────────────────────────────────────────────────────────────────

async def cb_an_calendar(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "Выбери год:",
        reply_markup=years_keyboard(_calendar_years(), "an_cal_year"),
    )


async def cb_an_cal_year(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    year = int(q.data.split(":")[1])
    await q.edit_message_text(
        f"Выбери месяц ({year}):",
        reply_markup=months_keyboard(year, "an_cal_month"),
    )


async def cb_an_cal_month(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    _, year_s, month_s = q.data.split(":")
    year, month = int(year_s), int(month_s)
    events = await db.get_events_by_month(year, month)
    text = fmt_calendar(year, month, events)
    await q.edit_message_text(
        text,
        reply_markup=back_keyboard(f"an_cal_year:{year}"),
        parse_mode="HTML",
    )


# ── Bush history ──────────────────────────────────────────────────────────────

async def cb_an_bush_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    varieties = await db.get_all_varieties()
    if not varieties:
        await q.edit_message_text("Нет данных.", reply_markup=back_keyboard("menu:analytics"))
        return
    await q.edit_message_text(
        "Выбери сорт:",
        reply_markup=varieties_keyboard(varieties, "an_hist_var"),
    )


async def cb_an_hist_var(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    vid = int(q.data.split(":")[1])
    variety = await db.get_variety_by_id(vid)
    events = await db.get_events_by_variety(vid)
    chunks = fmt_variety_history(variety["name"], events)
    for i, chunk in enumerate(chunks):
        if i == len(chunks) - 1:
            await q.message.reply_text(chunk, parse_mode="HTML", reply_markup=back_keyboard("an:bush_history"))
        else:
            await q.message.reply_text(chunk, parse_mode="HTML")


# ── Phenology ─────────────────────────────────────────────────────────────────

async def cb_an_phenology(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "Выбери год:",
        reply_markup=years_keyboard(_current_years(), "an_phen_year"),
    )


async def cb_an_phen_year(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    year = int(q.data.split(":")[1])
    rows = await db.get_phenology(year)
    await q.edit_message_text(
        fmt_phenology(year, rows),
        reply_markup=back_keyboard("an:phenology"),
        parse_mode="HTML",
    )


# ── Harvest ───────────────────────────────────────────────────────────────────

async def cb_an_harvest(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "Выбери год:",
        reply_markup=years_keyboard(_current_years(), "an_harv_year"),
    )


async def cb_an_harv_year(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    year = int(q.data.split(":")[1])
    rows = await db.get_harvest_by_year(year)
    await q.edit_message_text(
        fmt_harvest(year, rows),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("По сорту (все годы)", callback_data="an_harv_variety")],
            [InlineKeyboardButton("« Назад", callback_data="an:harvest")],
        ]),
        parse_mode="HTML",
    )


async def cb_an_harv_variety(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    varieties = await db.get_all_varieties()
    await q.edit_message_text(
        "Выбери сорт для истории урожаев:",
        reply_markup=varieties_keyboard(varieties, "an_harv_var"),
    )


async def cb_an_harv_var(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    vid = int(q.data.split(":")[1])
    variety = await db.get_variety_by_id(vid)
    rows = await db.get_harvest_by_variety_all_years(vid)
    if not rows:
        text = f"🍇 <b>{variety['name']}</b>: урожаев не записано."
    else:
        lines = [f"🍇 <b>{variety['name']} — урожай по годам</b>\n"]
        for r in rows:
            lines.append(f"  {r['year']}: {r['total_kg']:.1f} кг  ({r['picks']} сборов)")
        text = "\n".join(lines)
    await q.edit_message_text(text, reply_markup=back_keyboard("an:harvest"), parse_mode="HTML")


# ── Treatments ────────────────────────────────────────────────────────────────

async def cb_an_treatments(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "Выбери год:",
        reply_markup=years_keyboard(_current_years(), "an_treat_year"),
    )


async def cb_an_treat_year(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    year = int(q.data.split(":")[1])
    rows = await db.get_treatment_count_per_variety(year)
    await q.edit_message_text(
        fmt_treatments(year, rows),
        reply_markup=back_keyboard("an:treatments"),
        parse_mode="HTML",
    )


# ── Products usage ────────────────────────────────────────────────────────────

async def cb_an_products(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "Выбери год:",
        reply_markup=years_keyboard(_current_years(), "an_prod_year"),
    )


async def cb_an_prod_year(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    year = int(q.data.split(":")[1])
    rows = await db.get_products_usage(year)
    text = fmt_products_usage(year, rows)
    if len(text) > 4000:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for i, chunk in enumerate(chunks):
            if i == len(chunks) - 1:
                await q.message.reply_text(chunk, parse_mode="HTML", reply_markup=back_keyboard("an:products"))
            else:
                await q.message.reply_text(chunk, parse_mode="HTML")
    else:
        await q.edit_message_text(text, reply_markup=back_keyboard("an:products"), parse_mode="HTML")


# ── Cuttings stats ────────────────────────────────────────────────────────────

async def cb_an_cuttings(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "Выбери год:",
        reply_markup=years_keyboard(_current_years(), "an_cut_year"),
    )


async def cb_an_cut_year(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    year = int(q.data.split(":")[1])
    rows = await db.get_cuttings_stats(year)
    await q.edit_message_text(
        fmt_cuttings_stats(year, rows),
        reply_markup=back_keyboard("an:cuttings"),
        parse_mode="HTML",
    )
