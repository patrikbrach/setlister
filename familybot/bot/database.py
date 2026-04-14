"""SQLite database helpers for the shopping list."""

import sqlite3
import datetime
import os

DB_PATH = os.environ.get("DB_PATH", "/app/data/shopping.db")


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shopping_list (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                item         TEXT NOT NULL,
                added_by     TEXT NOT NULL,
                added_at     DATETIME NOT NULL,
                completed    BOOLEAN NOT NULL DEFAULT 0,
                completed_at DATETIME,
                completed_by TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS todo_list (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                item         TEXT NOT NULL,
                added_by     TEXT NOT NULL,
                added_at     DATETIME NOT NULL,
                completed    BOOLEAN NOT NULL DEFAULT 0,
                completed_at DATETIME,
                completed_by TEXT
            )
        """)
        conn.commit()


# --- Todo list ---

def todo_add(item: str, added_by: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO todo_list (item, added_by, added_at) VALUES (?, ?, ?)",
            (item.strip(), added_by, datetime.datetime.now()),
        )
        conn.commit()


def todo_get_all() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM todo_list ORDER BY completed, id"
        ).fetchall()


def todo_complete(position: int, completed_by: str) -> str | None:
    """Mark the Nth active item as completed. Returns item text or None if not found."""
    with get_connection() as conn:
        active = conn.execute(
            "SELECT id, item FROM todo_list WHERE completed=0 ORDER BY id"
        ).fetchall()
        if position < 1 or position > len(active):
            return None
        row = active[position - 1]
        conn.execute(
            "UPDATE todo_list SET completed=1, completed_at=?, completed_by=? WHERE id=?",
            (datetime.datetime.now(), completed_by, row["id"]),
        )
        conn.commit()
        return row["item"]


def todo_delete_completed() -> int:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM todo_list WHERE completed=1")
        conn.commit()
        return cursor.rowcount


def add_item(item: str, added_by: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO shopping_list (item, added_by, added_at) VALUES (?, ?, ?)",
            (item.strip(), added_by, datetime.datetime.now()),
        )
        conn.commit()


def get_all_items() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM shopping_list ORDER BY completed, added_at"
        ).fetchall()


def complete_item(item: str, completed_by: str) -> bool:
    """Mark matching active item as completed. Returns True if found."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM shopping_list WHERE lower(item)=lower(?) AND completed=0",
            (item.strip(),),
        ).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE shopping_list SET completed=1, completed_at=?, completed_by=? WHERE id=?",
            (datetime.datetime.now(), completed_by, row["id"]),
        )
        conn.commit()
        return True


def undo_item(item: str) -> bool:
    """Revert a completed item back to active. Returns True if found."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM shopping_list WHERE lower(item)=lower(?) AND completed=1",
            (item.strip(),),
        ).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE shopping_list SET completed=0, completed_at=NULL, completed_by=NULL WHERE id=?",
            (row["id"],),
        )
        conn.commit()
        return True


def delete_completed() -> int:
    """Delete all completed items. Returns number of deleted rows."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM shopping_list WHERE completed=1")
        conn.commit()
        return cursor.rowcount


def delete_all() -> int:
    """Delete every item in the list. Returns number of deleted rows."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM shopping_list")
        conn.commit()
        return cursor.rowcount
