import aiosqlite
from bot.config import DB_PATH

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS varieties (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    notes       TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    category    TEXT NOT NULL CHECK(category IN ('treatment','fertilizing')),
    notes       TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    variety_id      INTEGER NOT NULL REFERENCES varieties(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
    date            TEXT NOT NULL,
    weight_kg       REAL,
    product_id      INTEGER REFERENCES products(id) ON DELETE SET NULL,
    note            TEXT,
    photo_file_id   TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cuttings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    variety_id      INTEGER NOT NULL REFERENCES varieties(id) ON DELETE CASCADE,
    season          INTEGER NOT NULL,
    cut_date        TEXT,
    cut_count       INTEGER DEFAULT 0,
    storage_notes   TEXT,
    rooting_count   INTEGER DEFAULT 0,
    rooted_count    INTEGER DEFAULT 0,
    potted_count    INTEGER DEFAULT 0,
    sold_count      INTEGER DEFAULT 0,
    sold_to         TEXT,
    planted_count   INTEGER DEFAULT 0,
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS templates (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    event_type      TEXT NOT NULL,
    default_product_id  INTEGER REFERENCES products(id) ON DELETE SET NULL,
    default_note    TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_events_variety   ON events(variety_id);
CREATE INDEX IF NOT EXISTS idx_events_date      ON events(date);
CREATE INDEX IF NOT EXISTS idx_events_type_date ON events(event_type, date);
CREATE INDEX IF NOT EXISTS idx_cuttings_variety ON cuttings(variety_id);
CREATE INDEX IF NOT EXISTS idx_cuttings_season  ON cuttings(season);
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()
