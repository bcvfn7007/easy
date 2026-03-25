import aiosqlite
import os
from app.config.settings import config
from app.utils.logger import setup_logger

logger = setup_logger("database")

def get_db() -> aiosqlite.Connection:
    """Gets a new database connection."""
    # config.DATABASE_URL usually starts with sqlite+aiosqlite:///
    db_path = config.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    if not db_path.endswith(".db"):
        db_path = os.path.join(config.DATA_DIR, "easy_english.db")
    
    return aiosqlite.connect(db_path, timeout=15.0)

async def init_db():
    """Initializes the SQLite database tables."""
    logger.info("Initializing database...")
    async with get_db() as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                is_admin BOOLEAN DEFAULT 0,
                is_pro BOOLEAN DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ai_enabled BOOLEAN DEFAULT 1,
                voice_enabled BOOLEAN DEFAULT 1,
                language_level TEXT DEFAULT 'unknown'
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT, -- 'user' or 'assistant'
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        await db.commit()
    logger.info("Database initialized successfully.")
