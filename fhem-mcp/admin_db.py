import aiosqlite
import hashlib

DB_PATH = "admin.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                api_key TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def add_instance(name: str, url: str, api_key: str = None) -> int:
    """Insert a FHEM instance and return its new row id."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO instances (name, url, api_key) VALUES (?, ?, ?)",
            (name, url, api_key),
        )
        await db.commit()
        return cursor.lastrowid


async def update_instance(instance_id: int, name: str, url: str, api_key: str = None) -> bool:
    """Update an existing instance in place. Returns True when a row was updated."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE instances SET name = ?, url = ?, api_key = ? WHERE id = ?",
            (name, url, api_key, instance_id),
        )
        await db.commit()
        return cursor.rowcount > 0


async def get_instances():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, name, url, api_key FROM instances")
        return await cursor.fetchall()


async def delete_instance(instance_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM instances WHERE id = ?", (instance_id,))
        await db.commit()


def _hash_token(token: str) -> str:
    """Hash a token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


async def add_token(token: str):
    """Add a new API token to the database (stored as hash)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO api_keys (key_hash) VALUES (?)", (_hash_token(token),))
        await db.commit()


async def get_tokens():
    """Get all API tokens from the database (returns hashed tokens)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT key_hash FROM api_keys")
        return [row[0] for row in await cursor.fetchall()]


async def delete_token(token_hash: str):
    """Delete an API token by its hash."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM api_keys WHERE key_hash = ?", (token_hash,))
        await db.commit()


async def verify_token(token: str) -> bool:
    """Verify if a token exists in the database."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM api_keys WHERE key_hash = ?", (_hash_token(token),))
        return await cursor.fetchone() is not None
