"""SQLite 连接、建表与向前兼容迁移（V1.0 / V1.1 / V1.2 的数据库都可以直接升级）。"""
import sqlite3
from pathlib import Path

from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    favorite INTEGER NOT NULL DEFAULT 0 CHECK (favorite IN (0, 1)),
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TEXT
);

CREATE TABLE IF NOT EXISTS contact_methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    value TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
);
"""

# 索引一律在补列之后创建：V1.0/V1.1 的旧库还没有 label / deleted_at 列。
INDEXES = """
CREATE INDEX IF NOT EXISTS idx_contacts_favorite ON contacts(favorite);
CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(name);
CREATE INDEX IF NOT EXISTS idx_contacts_deleted ON contacts(deleted_at);
CREATE INDEX IF NOT EXISTS idx_methods_contact ON contact_methods(contact_id, sort_order);
"""

# (表名, 列名, 补列语句)。按顺序执行，重复执行是安全的（先查 table_info）。
MIGRATIONS = [
    ("contact_methods", "label", "ALTER TABLE contact_methods ADD COLUMN label TEXT NOT NULL DEFAULT ''"),
    ("contacts", "deleted_at", "ALTER TABLE contacts ADD COLUMN deleted_at TEXT"),
]


def get_db():
    if "db" not in g:
        database = current_app.config["DATABASE"]
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(database, timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA busy_timeout = 5000")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _table_columns(db, table):
    return {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}


def init_db():
    """建表并按需补列：兼容 V1.0（contact_methods 无 label）与 V1.1（contacts 无 deleted_at）数据库。"""
    db = get_db()
    db.executescript(SCHEMA)
    for table, column, statement in MIGRATIONS:
        if column not in _table_columns(db, table):
            db.execute(statement)
    db.executescript(INDEXES)
    db.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
