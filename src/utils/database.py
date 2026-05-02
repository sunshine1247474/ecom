"""
SQLite Database Layer
=====================
Stores product candidates, their scores, and decisions.
All data lives in data/resale_scanner.db — no external DB needed.
"""

from __future__ import annotations
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional


DB_PATH = Path(__file__).parent.parent.parent / "data" / "resale_scanner.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at      TEXT    NOT NULL,
            updated_at      TEXT    NOT NULL,
            title           TEXT    NOT NULL,
            keyword         TEXT,
            category        TEXT,
            source          TEXT,
            source_url      TEXT,
            source_price    REAL,
            sale_price      REAL,
            shipping_out    REAL    DEFAULT 0,
            shipping_in     REAL    DEFAULT 0,
            packaging_cost  REAL    DEFAULT 0.30,
            promoted_rate   REAL    DEFAULT 0.07,
            buyer_state     TEXT    DEFAULT 'TX',
            weight_lbs      REAL    DEFAULT 1.0,
            is_branded      INTEGER DEFAULT 0,
            is_fragile      INTEGER DEFAULT 0,
            is_hazmat       INTEGER DEFAULT 0,
            is_regulated    INTEGER DEFAULT 0,
            return_rate_high INTEGER DEFAULT 0,
            -- Computed fields (stored for history)
            net_margin_before_cashback  REAL,
            net_profit_before_cashback  REAL,
            cashback_expected           REAL    DEFAULT 0,
            net_profit_after_cashback   REAL,
            final_score                 REAL,
            decision                    TEXT,
            notes                       TEXT,
            status                      TEXT    DEFAULT 'candidate'
            -- status: candidate | approved | testing | live | rejected | archived
        );

        CREATE TABLE IF NOT EXISTS cashback_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id      INTEGER REFERENCES products(id),
            created_at      TEXT    NOT NULL,
            retailer        TEXT,
            purchase_amount REAL,
            program         TEXT,
            advertised_rate REAL,
            expected_value  REAL,
            actual_received REAL,
            notes           TEXT
        );
    """)
    conn.commit()
    conn.close()


def upsert_product(data: dict) -> int:
    """Insert or update a product. Returns the row id."""
    conn = get_connection()
    now = datetime.utcnow().isoformat()

    existing_id = data.get("id")
    if existing_id:
        cols = [k for k in data if k != "id"]
        set_clause = ", ".join(f"{c} = ?" for c in cols)
        values = [data[c] for c in cols] + [existing_id]
        conn.execute(
            f"UPDATE products SET updated_at = ?, {set_clause} WHERE id = ?",
            [now] + values,
        )
        conn.commit()
        conn.close()
        return existing_id
    else:
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        cols = list(data.keys())
        placeholders = ", ".join("?" for _ in cols)
        values = list(data.values())
        cur = conn.execute(
            f"INSERT INTO products ({', '.join(cols)}) VALUES ({placeholders})",
            values,
        )
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return new_id


def get_all_products(status: Optional[str] = None) -> list[dict]:
    conn = get_connection()
    if status:
        rows = conn.execute(
            "SELECT * FROM products WHERE status = ? ORDER BY final_score DESC",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM products ORDER BY final_score DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_status(product_id: int, status: str):
    conn = get_connection()
    conn.execute(
        "UPDATE products SET status = ?, updated_at = ? WHERE id = ?",
        (status, datetime.utcnow().isoformat(), product_id),
    )
    conn.commit()
    conn.close()


def delete_product(product_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()


def log_cashback(
    product_id: int,
    retailer: str,
    purchase_amount: float,
    program: str,
    advertised_rate: float,
    expected_value: float,
    actual_received: float = 0.0,
    notes: str = "",
):
    conn = get_connection()
    conn.execute(
        """INSERT INTO cashback_log
           (product_id, created_at, retailer, purchase_amount, program,
            advertised_rate, expected_value, actual_received, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            product_id,
            datetime.utcnow().isoformat(),
            retailer, purchase_amount, program,
            advertised_rate, expected_value, actual_received, notes,
        ),
    )
    conn.commit()
    conn.close()


# Initialize on import
init_db()
