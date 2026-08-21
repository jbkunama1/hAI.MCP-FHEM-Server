import aiosqlite
import os

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

async def add_instance(name: str, url: str, api_key: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO instances (name, url, api_key) VALUES (?, ?, ?)", (name, url, api_key))
        await db.commit()

async def get_instances():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, name, url, api_key FROM instances")
        return await cursor.fetchall()

async def delete_instance(instance_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM instances WHERE id = ?", (instance_id,))
        await db.commit()
