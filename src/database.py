"""SQLite database layer for achievement tracking."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "achievements.db"


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory enabled."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create the achievements table if it doesn't exist."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                situation TEXT NOT NULL,
                action TEXT NOT NULL,
                result TEXT,
                tags TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0,
                notion_page_id TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a database row to a dictionary with parsed tags."""
    d = dict(row)
    d["tags"] = json.loads(d["tags"])
    d["archived"] = bool(d["archived"])
    return d


def add_achievement(
    situation: str,
    action: str,
    result: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Add a new achievement and return it."""
    now = datetime.now().isoformat()
    tags_json = json.dumps(tags or [])
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO achievements
            (situation, action, result, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (situation, action, result, tags_json, now, now),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM achievements WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_achievement_by_id(achievement_id: int) -> dict[str, Any] | None:
    """Get a single achievement by ID."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM achievements WHERE id = ?", (achievement_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def get_achievements(include_archived: bool = False) -> list[dict[str, Any]]:
    """Get all achievements, optionally including archived ones."""
    conn = get_connection()
    try:
        if include_archived:
            rows = conn.execute(
                "SELECT * FROM achievements ORDER BY created_at DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM achievements WHERE archived = 0 ORDER BY created_at DESC"
            ).fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def update_achievement(
    achievement_id: int,
    situation: str | None = None,
    action: str | None = None,
    result: str | None = ...,  # type: ignore[assignment]
    tags: list[str] | None = None,
) -> dict[str, Any] | None:
    """Update an achievement. Only provided fields are updated."""
    existing = get_achievement_by_id(achievement_id)
    if not existing:
        return None

    now = datetime.now().isoformat()
    new_situation = situation if situation is not None else existing["situation"]
    new_action = action if action is not None else existing["action"]
    new_result = result if result is not ... else existing["result"]
    new_tags = json.dumps(tags if tags is not None else existing["tags"])

    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE achievements
            SET situation = ?, action = ?, result = ?, tags = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_situation, new_action, new_result, new_tags, now, achievement_id),
        )
        conn.commit()
        return get_achievement_by_id(achievement_id)
    finally:
        conn.close()


def delete_achievement(achievement_id: int) -> bool:
    """Delete an achievement. Returns True if it existed."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM achievements WHERE id = ?", (achievement_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def toggle_archive(achievement_id: int) -> dict[str, Any] | None:
    """Toggle the archived status of an achievement."""
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE achievements
            SET archived = CASE WHEN archived = 0 THEN 1 ELSE 0 END,
                updated_at = ?
            WHERE id = ?
            """,
            (datetime.now().isoformat(), achievement_id),
        )
        conn.commit()
        return get_achievement_by_id(achievement_id)
    finally:
        conn.close()


def get_all_tags() -> list[dict[str, Any]]:
    """Get all unique tags with their usage counts."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT tags FROM achievements WHERE archived = 0"
        ).fetchall()
        tag_counts: dict[str, int] = {}
        for row in rows:
            for tag in json.loads(row["tags"]):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        return [
            {"tag": tag, "count": count}
            for tag, count in sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))
        ]
    finally:
        conn.close()


def search_achievements(
    query: str | None = None,
    tags: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    include_archived: bool = False,
) -> list[dict[str, Any]]:
    """Search achievements with optional filters."""
    conditions: list[str] = []
    params: list[Any] = []

    if not include_archived:
        conditions.append("archived = 0")

    if query:
        conditions.append("(situation LIKE ? OR action LIKE ? OR result LIKE ?)")
        like_query = f"%{query}%"
        params.extend([like_query, like_query, like_query])

    if date_from:
        conditions.append("created_at >= ?")
        params.append(date_from)

    if date_to:
        conditions.append("created_at <= ?")
        # Include the full day by appending end-of-day time
        params.append(date_to + "T23:59:59")

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    sql = f"SELECT * FROM achievements WHERE {where_clause} ORDER BY created_at DESC"

    conn = get_connection()
    try:
        rows = conn.execute(sql, params).fetchall()
        results = [_row_to_dict(row) for row in rows]

        # Filter by tags in Python (JSON array in SQLite)
        if tags:
            results = [r for r in results if any(t in r["tags"] for t in tags)]

        return results
    finally:
        conn.close()


def set_notion_page_id(achievement_id: int, notion_page_id: str) -> None:
    """Store the Notion page ID after promoting an achievement."""
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE achievements
            SET notion_page_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (notion_page_id, datetime.now().isoformat(), achievement_id),
        )
        conn.commit()
    finally:
        conn.close()
