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
    async with get_db() as db:
        await db.execute('''
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        ''', (key, value))
        await db.commit()

async def get_global_setting(key: str, default: str = None) -> Optional[str]:
    async with get_db() as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else default

async def is_trial_active(user_id: int) -> bool:
    """Returns True if the user created their account within the last 15 days."""
    async with get_db() as db:
        async with db.execute("SELECT (julianday('now') - julianday(joined_at)) FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0] is not None:
                return row[0] <= 15.0
            return True # fallback on null

async def get_user_setting(user_id: int, key: str, default: str = 'auto') -> str:
    """Gets a specific user setting like tts_language."""
    async with get_db() as db:
        try:
            async with db.execute(f"SELECT {key} FROM user_settings WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else default
        except aiosqlite.OperationalError:
            return default # column might not exist

async def set_user_setting(user_id: int, key: str, value: str) -> None:
    """Sets a user setting."""
    async with get_db() as db:
        # SQLite UPSERT syntax
        await db.execute(f'''
            INSERT INTO user_settings (user_id, {key}) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET {key} = excluded.{key}
        ''', (user_id, value))
        await db.commit()

async def get_user_stats(user_id: int) -> dict:
    """Gets usage statistics for a user."""
    stats = {"messages_sent": 0, "trial_days_left": 0}
    async with get_db() as db:
        # Get message count
        async with db.execute("SELECT COUNT(*) FROM messages WHERE user_id = ? AND role = 'user'", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                stats["messages_sent"] = row[0]
                
        # Get trial days left
        async with db.execute("SELECT (julianday('now') - julianday(joined_at)) FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row[0] is not None:
                days_used = row[0]
                stats["trial_days_left"] = max(0, 15 - int(days_used))
            else:
                stats["trial_days_left"] = 15
                
    return stats

async def update_user_grammar_level(user_id: int, level: str) -> None:
    """Updates user language/grammar level."""
    async with get_db() as db:
        await db.execute("UPDATE users SET language_level = ? WHERE user_id = ?", (level, user_id))
        await db.commit()

async def add_to_vault(user_id: int, content: str) -> None:
    """Saves a corrected rule or vocabulary to the personal vault."""
    async with get_db() as db:
        await db.execute("INSERT INTO vault (user_id, content) VALUES (?, ?)", (user_id, content))
        await db.commit()
        
async def get_vault_items(user_id: int, limit: int = 20) -> List[str]:
    """Retrieves vault items for a user."""
    async with get_db() as db:
        async with db.execute("SELECT content FROM vault WHERE user_id = ? ORDER BY added_at DESC LIMIT ?", (user_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def update_user_activity(user_id: int) -> dict:
    """Updates last_active and manages the Daily Streak logic."""
    async with get_db() as db:
        async with db.execute("SELECT streak_count, DATE(last_active) == DATE('now'), DATE(last_active) == DATE('now', '-1 day') FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return {"streak": 0, "new_day": False}
                
            current_streak, is_today, is_yesterday = row
            
            new_streak = current_streak
            new_day = False
            
            if is_yesterday:
                new_streak += 1
                new_day = True
            elif not is_today and not is_yesterday:
                # Streak broken or first time
                new_streak = 1
                new_day = True
                
            if new_day or new_streak == 0:
                if new_streak == 0: new_streak = 1
                await db.execute("UPDATE users SET streak_count = ?, last_active = CURRENT_TIMESTAMP WHERE user_id = ?", (new_streak, user_id))
                await db.commit()
                
            return {"streak": new_streak, "new_day": new_day}

