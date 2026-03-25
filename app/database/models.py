import json
from typing import Optional, List, Dict
from app.database.db import get_db
import aiosqlite
from app.utils.logger import setup_logger

logger = setup_logger("db_models")

async def get_user(user_id: int) -> Optional[dict]:
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def create_or_update_user(user_id: int, username: str, first_name: str) -> None:
    async with get_db() as db:
        await db.execute('''
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
        ''', (user_id, username, first_name))
        await db.commit()

async def get_all_users() -> List[int]:
    async with get_db() as db:
        async with db.execute("SELECT user_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def toggle_user_status(user_id: int, status_field: str, value: int) -> None:
    """Toggles fields like is_admin, is_pro."""
    allowed_fields = ['is_admin', 'is_pro']
    if status_field not in allowed_fields:
        return
    async with get_db() as db:
        await db.execute(f"UPDATE users SET {status_field} = ? WHERE user_id = ?", (value, user_id))
        await db.commit()

async def update_user_feature(user_id: int, feature: str, value: int) -> None:
    """Toggles ai_enabled, voice_enabled per user."""
    allowed_fields = ['ai_enabled', 'voice_enabled']
    if feature not in allowed_fields:
        return
    async with get_db() as db:
        await db.execute(f"UPDATE users SET {feature} = ? WHERE user_id = ?", (value, user_id))
        await db.commit()

async def add_message_to_history(user_id: int, role: str, content: str) -> int:
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, role, content)
        )
        await db.commit()
        return cursor.lastrowid

async def get_message_history(user_id: int, limit: int = 10) -> List[Dict[str, str]]:
    """Retrieves the last `limit` messages for context."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT role, content FROM messages WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            # Return in chronological order
            return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

async def set_global_setting(key: str, value: str) -> None:
    async with await get_db() as db:
        await db.execute('''
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        ''', (key, value))
        await db.commit()

async def get_global_setting(key: str, default: str = None) -> Optional[str]:
    async with await get_db() as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else default
