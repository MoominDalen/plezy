"""SQLite persistence for products and settings."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ProductRow:
    id: int
    source: str
    name: str
    url: str
    sku: str | None
    image_url: str | None
    enabled: bool
    available: bool | None
    status_message: str | None
    last_checked: str | None
    created_at: str
    updated_at: str


class Database:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL DEFAULT 'johnlewis',
                    name TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    sku TEXT,
                    image_url TEXT,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    available INTEGER,
                    status_message TEXT,
                    last_checked TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS pokemoncenter_status (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    queue_active INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'unknown',
                    detail TEXT,
                    checked_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO pokemoncenter_status (id, queue_active, status, detail, checked_at)
                VALUES (1, 0, 'unknown', NULL, ?)
                """,
                (_utc_now(),),
            )

    def list_products(self, *, source: str | None = None) -> list[ProductRow]:
        query = "SELECT * FROM products"
        params: list[Any] = []
        if source:
            query += " WHERE source = ?"
            params.append(source)
        query += " ORDER BY name COLLATE NOCASE"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_row_to_product(r) for r in rows]

    def get_product(self, product_id: int) -> ProductRow | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM products WHERE id = ?", (product_id,)
            ).fetchone()
        return _row_to_product(row) if row else None

    def upsert_product(
        self,
        *,
        url: str,
        name: str,
        source: str = "johnlewis",
        sku: str | None = None,
        image_url: str | None = None,
        enabled: bool = True,
    ) -> ProductRow:
        now = _utc_now()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM products WHERE url = ?", (url,)
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE products
                    SET name = ?, source = ?, sku = COALESCE(?, sku),
                        image_url = COALESCE(?, image_url),
                        enabled = ?, updated_at = ?
                    WHERE url = ?
                    """,
                    (name, source, sku, image_url, int(enabled), now, url),
                )
                product_id = int(existing["id"])
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO products
                    (source, name, url, sku, image_url, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (source, name, url, sku, image_url, int(enabled), now, now),
                )
                product_id = int(cursor.lastrowid)
        row = self.get_product(product_id)
        assert row is not None
        return row

    def update_product(
        self,
        product_id: int,
        *,
        name: str | None = None,
        url: str | None = None,
        sku: str | None = None,
        image_url: str | None = None,
        enabled: bool | None = None,
    ) -> ProductRow | None:
        product = self.get_product(product_id)
        if not product:
            return None
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE products SET
                    name = COALESCE(?, name),
                    url = COALESCE(?, url),
                    sku = COALESCE(?, sku),
                    image_url = COALESCE(?, image_url),
                    enabled = COALESCE(?, enabled),
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    name,
                    url,
                    sku,
                    image_url,
                    int(enabled) if enabled is not None else None,
                    now,
                    product_id,
                ),
            )
        return self.get_product(product_id)

    def update_stock(
        self,
        product_id: int,
        *,
        available: bool,
        status_message: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE products
                SET available = ?, status_message = ?, last_checked = ?, updated_at = ?
                WHERE id = ?
                """,
                (int(available), status_message, _utc_now(), _utc_now(), product_id),
            )

    def delete_product(self, product_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        return cursor.rowcount > 0

    def get_setting(self, key: str, default: str = "") -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            ).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def all_settings(self) -> dict[str, str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {str(r["key"]): str(r["value"]) for r in rows}

    def update_pokemoncenter(
        self, *, queue_active: bool, status: str, detail: str | None
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE pokemoncenter_status
                SET queue_active = ?, status = ?, detail = ?, checked_at = ?
                WHERE id = 1
                """,
                (int(queue_active), status, detail, _utc_now()),
            )

    def get_pokemoncenter(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM pokemoncenter_status WHERE id = 1"
            ).fetchone()
        return dict(row) if row else {}


def _row_to_product(row: sqlite3.Row) -> ProductRow:
    return ProductRow(
        id=int(row["id"]),
        source=str(row["source"]),
        name=str(row["name"]),
        url=str(row["url"]),
        sku=row["sku"],
        image_url=row["image_url"],
        enabled=bool(row["enabled"]),
        available=None if row["available"] is None else bool(row["available"]),
        status_message=row["status_message"],
        last_checked=row["last_checked"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def import_yaml_products(db: Database, config_path: Path) -> int:
    """One-time import from legacy config.yaml."""
    if not config_path.exists():
        return 0
    import yaml

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    count = 0
    for entry in data.get("products") or []:
        if not isinstance(entry, dict):
            continue
        url = str(entry.get("url", "")).strip()
        if not url:
            continue
        name = str(entry.get("name") or "Product").strip()
        sku = str(entry.get("sku") or "").strip() or None
        db.upsert_product(url=url, name=name, sku=sku, source="johnlewis")
        count += 1
    return count
