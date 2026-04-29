"""Message text formatters."""
from __future__ import annotations

from bot.utils.keyboards import EVENT_TYPES

MONTH_NAMES_RU = [
    "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]

MONTH_NAMES_GEN = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def fmt_date(iso: str) -> str:
    """'2024-05-15' → '15 мая 2024'"""
    try:
        y, m, d = iso.split("-")
        return f"{int(d)} {MONTH_NAMES_GEN[int(m)]} {y}"
    except Exception:
        return iso


def fmt_event(e: dict) -> str:
    label = EVENT_TYPES.get(e["event_type"], e["event_type"])
    parts = [f"{label}  —  {fmt_date(e['date'])}"]
    if e.get("product_name"):
        parts.append(f"Препарат/удобрение: {e['product_name']}")
    if e.get("weight_kg") is not None:
        parts.append(f"Вес: {e['weight_kg']} кг")
    if e.get("note"):
        parts.append(f"Заметка: {e['note']}")
    return "\n".join(parts)


def fmt_variety_history(variety_name: str, events: list[dict]) -> list[str]:
    """Returns list of message chunks (≤4000 chars each)."""
    lines = [f"📋 <b>История: {variety_name}</b>\n"]
    for e in events:
        lines.append(fmt_event(e))
    return _split_chunks(lines)


def fmt_calendar(year: int, month: int, events: list[dict]) -> str:
    header = f"📅 <b>{MONTH_NAMES_RU[month]} {year}</b>\n"
    if not events:
        return header + "Событий нет."
    by_date: dict[str, list[dict]] = {}
    for e in events:
        by_date.setdefault(e["date"], []).append(e)
    lines = [header]
    for d in sorted(by_date):
        lines.append(f"\n<b>{fmt_date(d)}</b>")
        for e in by_date[d]:
            label = EVENT_TYPES.get(e["event_type"], e["event_type"])
            line = f"  • {e['variety_name']} — {label}"
            if e.get("product_name"):
                line += f" ({e['product_name']})"
            if e.get("weight_kg"):
                line += f" {e['weight_kg']} кг"
            if e.get("note"):
                line += f"  <i>{e['note']}</i>"
            lines.append(line)
    return "\n".join(lines)


def fmt_harvest(year: int, rows: list[dict]) -> str:
    if not rows:
        return f"🍇 Урожай за {year}: данных нет."
    total = sum(r["total_kg"] or 0 for r in rows)
    lines = [f"🍇 <b>Урожай {year}</b>  (всего {total:.1f} кг)\n"]
    for r in rows:
        kg = r["total_kg"] or 0
        lines.append(f"  {r['name']}: {kg:.1f} кг  ({r['picks']} сборов)")
    return "\n".join(lines)


def fmt_phenology(year: int, rows: list[dict]) -> str:
    if not rows:
        return f"🌸 Фенология {year}: данных нет."
    lines = [f"🌸 <b>Фенология {year}</b>\n"]
    lines.append(f"{'Сорт':<22} {'Цветение':<14} {'Созревание'}")
    lines.append("─" * 52)
    for r in rows:
        fl = fmt_date(r["flowering_date"]) if r["flowering_date"] else "—"
        rp = fmt_date(r["ripening_date"]) if r["ripening_date"] else "—"
        lines.append(f"{r['name']:<22} {fl:<14} {rp}")
    return "<pre>" + "\n".join(lines) + "</pre>"


def fmt_treatments(year: int, rows: list[dict]) -> str:
    if not rows:
        return f"💊 Обработки {year}: данных нет."
    lines = [f"💊 <b>Обработки {year}</b>\n"]
    for r in rows:
        lines.append(f"  {r['name']}: {r['treatments']} раз")
    return "\n".join(lines)


def fmt_products_usage(year: int, rows: list[dict]) -> str:
    if not rows:
        return f"🧪 Препараты {year}: данных нет."
    lines = [f"🧪 <b>Препараты и удобрения {year}</b>\n"]
    cur_product = None
    for r in rows:
        if r["product"] != cur_product:
            lines.append(f"\n<b>{r['product']}</b> [{r['category']}]")
            cur_product = r["product"]
        entry = f"  {fmt_date(r['date'])} — {r['variety_name']}"
        if r.get("note"):
            entry += f"  <i>{r['note']}</i>"
        lines.append(entry)
    return "\n".join(lines)


def fmt_cuttings_stats(season: int, rows: list[dict]) -> str:
    if not rows:
        return f"✂️ Черенки {season}: данных нет."
    lines = [f"✂️ <b>Черенки {season}</b>\n"]
    lines.append(f"{'Сорт':<20} {'Нарез'} {'Укор%'} {'Прод'} {'Высаж'}")
    lines.append("─" * 52)
    for r in rows:
        pct = f"{r['rooting_pct']}%" if r["rooting_pct"] is not None else "—"
        lines.append(
            f"{r['name']:<20} {r['cut_total'] or 0:>5} "
            f"{pct:>5}  {r['sold_total'] or 0:>4}  {r['planted_total'] or 0:>5}"
        )
    return "<pre>" + "\n".join(lines) + "</pre>"


def fmt_cutting_card(c: dict) -> str:
    lines = [f"✂️ <b>{c['variety_name']} — сезон {c['season']}</b>"]
    if c.get("cut_date"):
        lines.append(f"Нарезка: {fmt_date(c['cut_date'])}, {c['cut_count']} шт.")
    if c.get("storage_notes"):
        lines.append(f"Хранение: {c['storage_notes']}")
    if c.get("rooting_count"):
        lines.append(f"На укоренение: {c['rooting_count']} шт.")
    if c.get("rooted_count"):
        lines.append(f"Прижилось: {c['rooted_count']} шт.")
    if c.get("potted_count"):
        lines.append(f"В ёмкости: {c['potted_count']} шт.")
    if c.get("sold_count"):
        sold_line = f"Продано: {c['sold_count']} шт."
        if c.get("sold_to"):
            sold_line += f" → {c['sold_to']}"
        lines.append(sold_line)
    if c.get("planted_count"):
        lines.append(f"Высажено в грунт: {c['planted_count']} шт.")
    if c.get("notes"):
        lines.append(f"Заметка: {c['notes']}")
    return "\n".join(lines)


def _split_chunks(lines: list[str], max_len: int = 4000) -> list[str]:
    chunks, current = [], ""
    for line in lines:
        if len(current) + len(line) + 1 > max_len:
            if current:
                chunks.append(current)
            current = line
        else:
            current = current + "\n" + line if current else line
    if current:
        chunks.append(current)
    return chunks or ["Нет данных."]
