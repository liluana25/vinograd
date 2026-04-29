"""All database CRUD operations."""
from __future__ import annotations

import aiosqlite
from typing import Any
from bot.config import DB_PATH


# ─── helpers ────────────────────────────────────────────────────────────────

async def _fetchall(sql: str, params: tuple = ()) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql, params) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def _fetchone(sql: str, params: tuple = ()) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(sql, params) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def _execute(sql: str, params: tuple = ()) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(sql, params) as cur:
            await db.commit()
            return cur.lastrowid


# ─── varieties ──────────────────────────────────────────────────────────────

async def get_all_varieties() -> list[dict]:
    return await _fetchall("SELECT * FROM varieties ORDER BY name")


async def get_variety_by_id(vid: int) -> dict | None:
    return await _fetchone("SELECT * FROM varieties WHERE id=?", (vid,))


async def get_variety_by_name(name: str) -> dict | None:
    return await _fetchone("SELECT * FROM varieties WHERE name=?", (name,))


async def add_variety(name: str, notes: str = "") -> int:
    return await _execute(
        "INSERT INTO varieties (name, notes) VALUES (?,?)", (name, notes or None)
    )


async def rename_variety(vid: int, new_name: str) -> None:
    await _execute("UPDATE varieties SET name=? WHERE id=?", (new_name, vid))


async def update_variety_notes(vid: int, notes: str) -> None:
    await _execute("UPDATE varieties SET notes=? WHERE id=?", (notes, vid))


async def delete_variety(vid: int) -> None:
    await _execute("DELETE FROM varieties WHERE id=?", (vid,))


# ─── products ───────────────────────────────────────────────────────────────

async def get_all_products(category: str | None = None) -> list[dict]:
    if category:
        return await _fetchall(
            "SELECT * FROM products WHERE category=? ORDER BY name", (category,)
        )
    return await _fetchall("SELECT * FROM products ORDER BY name")


async def get_product_by_id(pid: int) -> dict | None:
    return await _fetchone("SELECT * FROM products WHERE id=?", (pid,))


async def add_product(name: str, category: str, notes: str = "") -> int:
    return await _execute(
        "INSERT INTO products (name, category, notes) VALUES (?,?,?)",
        (name, category, notes or None),
    )


async def rename_product(pid: int, new_name: str) -> None:
    await _execute("UPDATE products SET name=? WHERE id=?", (new_name, pid))


# ─── events ─────────────────────────────────────────────────────────────────

async def add_event(
    variety_id: int,
    event_type: str,
    date: str,
    weight_kg: float | None = None,
    product_id: int | None = None,
    note: str | None = None,
    photo_file_id: str | None = None,
) -> int:
    return await _execute(
        """INSERT INTO events
           (variety_id, event_type, date, weight_kg, product_id, note, photo_file_id)
           VALUES (?,?,?,?,?,?,?)""",
        (variety_id, event_type, date, weight_kg, product_id, note, photo_file_id),
    )


async def get_events_by_variety(vid: int) -> list[dict]:
    return await _fetchall(
        """SELECT e.*, p.name as product_name
           FROM events e LEFT JOIN products p ON e.product_id=p.id
           WHERE e.variety_id=? ORDER BY e.date, e.id""",
        (vid,),
    )


async def get_events_by_type_and_year(event_type: str, year: int) -> list[dict]:
    return await _fetchall(
        """SELECT e.*, v.name as variety_name, p.name as product_name
           FROM events e
           JOIN varieties v ON e.variety_id=v.id
           LEFT JOIN products p ON e.product_id=p.id
           WHERE e.event_type=? AND strftime('%Y', e.date)=?
           ORDER BY e.date""",
        (event_type, str(year)),
    )


async def get_events_by_month(year: int, month: int) -> list[dict]:
    ym = f"{year}-{month:02d}"
    return await _fetchall(
        """SELECT e.*, v.name as variety_name, p.name as product_name
           FROM events e
           JOIN varieties v ON e.variety_id=v.id
           LEFT JOIN products p ON e.product_id=p.id
           WHERE strftime('%Y-%m', e.date)=?
           ORDER BY e.date, v.name""",
        (ym,),
    )


async def get_harvest_by_year(year: int) -> list[dict]:
    return await _fetchall(
        """SELECT v.name, SUM(e.weight_kg) as total_kg, COUNT(*) as picks
           FROM events e JOIN varieties v ON e.variety_id=v.id
           WHERE e.event_type='harvest' AND strftime('%Y', e.date)=?
           GROUP BY v.id ORDER BY total_kg DESC""",
        (str(year),),
    )


async def get_harvest_by_variety_all_years(vid: int) -> list[dict]:
    return await _fetchall(
        """SELECT strftime('%Y', date) as year,
                  SUM(weight_kg) as total_kg, COUNT(*) as picks
           FROM events WHERE variety_id=? AND event_type='harvest'
           GROUP BY year ORDER BY year""",
        (vid,),
    )


async def get_phenology(year: int) -> list[dict]:
    return await _fetchall(
        """SELECT v.name,
                  MAX(CASE WHEN e.event_type='flowering' THEN e.date END) as flowering_date,
                  MAX(CASE WHEN e.event_type='ripening'  THEN e.date END) as ripening_date
           FROM events e JOIN varieties v ON e.variety_id=v.id
           WHERE strftime('%Y', e.date)=?
             AND e.event_type IN ('flowering','ripening')
           GROUP BY v.id ORDER BY flowering_date NULLS LAST""",
        (str(year),),
    )


async def get_treatment_count_per_variety(year: int) -> list[dict]:
    return await _fetchall(
        """SELECT v.name, COUNT(*) as treatments
           FROM events e JOIN varieties v ON e.variety_id=v.id
           WHERE e.event_type='treatment' AND strftime('%Y', e.date)=?
           GROUP BY v.id ORDER BY treatments DESC""",
        (str(year),),
    )


async def get_products_usage(year: int) -> list[dict]:
    return await _fetchall(
        """SELECT p.name as product, p.category, e.date, v.name as variety_name, e.note
           FROM events e
           JOIN varieties v ON e.variety_id=v.id
           JOIN products p ON e.product_id=p.id
           WHERE e.event_type IN ('treatment','fertilizing')
             AND strftime('%Y', e.date)=?
           ORDER BY e.date, p.name""",
        (str(year),),
    )


async def delete_event(event_id: int) -> None:
    await _execute("DELETE FROM events WHERE id=?", (event_id,))


# ─── cuttings ───────────────────────────────────────────────────────────────

async def add_cutting(variety_id: int, season: int, cut_date: str, cut_count: int,
                      storage_notes: str = "") -> int:
    return await _execute(
        """INSERT INTO cuttings (variety_id, season, cut_date, cut_count, storage_notes)
           VALUES (?,?,?,?,?)""",
        (variety_id, season, cut_date, cut_count, storage_notes or None),
    )


async def get_cuttings_by_variety(vid: int) -> list[dict]:
    return await _fetchall(
        """SELECT c.*, v.name as variety_name FROM cuttings c
           JOIN varieties v ON c.variety_id=v.id
           WHERE c.variety_id=? ORDER BY c.season DESC, c.cut_date DESC""",
        (vid,),
    )


async def get_cuttings_by_season(season: int) -> list[dict]:
    return await _fetchall(
        """SELECT c.*, v.name as variety_name FROM cuttings c
           JOIN varieties v ON c.variety_id=v.id
           WHERE c.season=? ORDER BY v.name""",
        (season,),
    )


async def get_cutting_by_id(cid: int) -> dict | None:
    return await _fetchone(
        """SELECT c.*, v.name as variety_name FROM cuttings c
           JOIN varieties v ON c.variety_id=v.id
           WHERE c.id=?""",
        (cid,),
    )


async def update_cutting(cid: int, **fields: Any) -> None:
    allowed = {
        "storage_notes", "rooting_count", "rooted_count",
        "potted_count", "sold_count", "sold_to", "planted_count", "notes",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k}=?" for k in updates)
    set_clause += ", updated_at=datetime('now')"
    values = list(updates.values()) + [cid]
    await _execute(f"UPDATE cuttings SET {set_clause} WHERE id=?", tuple(values))


async def get_cuttings_stats(season: int) -> list[dict]:
    return await _fetchall(
        """SELECT v.name,
                  SUM(c.cut_count)     as cut_total,
                  SUM(c.rooting_count) as rooting_total,
                  SUM(c.rooted_count)  as rooted_total,
                  SUM(c.sold_count)    as sold_total,
                  SUM(c.planted_count) as planted_total,
                  CASE WHEN SUM(c.rooting_count)>0
                       THEN ROUND(100.0*SUM(c.rooted_count)/SUM(c.rooting_count),1)
                       ELSE NULL END as rooting_pct
           FROM cuttings c JOIN varieties v ON c.variety_id=v.id
           WHERE c.season=?
           GROUP BY v.id ORDER BY v.name""",
        (season,),
    )


async def delete_cutting(cid: int) -> None:
    await _execute("DELETE FROM cuttings WHERE id=?", (cid,))


# ─── templates ──────────────────────────────────────────────────────────────

async def get_all_templates() -> list[dict]:
    return await _fetchall(
        """SELECT t.*, p.name as product_name FROM templates t
           LEFT JOIN products p ON t.default_product_id=p.id
           ORDER BY t.name"""
    )


async def get_template_by_id(tid: int) -> dict | None:
    return await _fetchone(
        """SELECT t.*, p.name as product_name FROM templates t
           LEFT JOIN products p ON t.default_product_id=p.id
           WHERE t.id=?""",
        (tid,),
    )


async def add_template(name: str, event_type: str,
                       default_product_id: int | None = None,
                       default_note: str = "") -> int:
    return await _execute(
        """INSERT INTO templates (name, event_type, default_product_id, default_note)
           VALUES (?,?,?,?)""",
        (name, event_type, default_product_id, default_note or None),
    )


async def delete_template(tid: int) -> None:
    await _execute("DELETE FROM templates WHERE id=?", (tid,))
