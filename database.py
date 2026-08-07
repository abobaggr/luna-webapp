# database.py
import os
import asyncpg
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in environment")

# ═══════════════════════════════════════════
# SYNC POOL (для Flask / инициализации таблиц)
# ═══════════════════════════════════════════
_sync_pool = SimpleConnectionPool(1, 5, DATABASE_URL)

@contextmanager
def get_db():
    conn = _sync_pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _sync_pool.putconn(conn)

def init_db_sync():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS models (
                    id SERIAL PRIMARY KEY,
                    manager_id BIGINT DEFAULT 0,
                    name TEXT NOT NULL,
                    age INT NOT NULL,
                    height INT,
                    bust INT,
                    city TEXT NOT NULL,
                    description TEXT,
                    price_1h INT NOT NULL,
                    price_2h INT,
                    price_night INT,
                    main_photo TEXT DEFAULT '',
                    gallery JSONB DEFAULT '[]',
                    is_active INT DEFAULT 1,
                    is_verified INT DEFAULT 0,
                    tags JSONB DEFAULT '[]',
                    views INT DEFAULT 0,
                    likes INT DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS clients (
                    id SERIAL PRIMARY KEY,
                    tg_id BIGINT UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    manager_id BIGINT,
                    ref_code TEXT,
                    bonus INT DEFAULT 0,
                    total_spent INT DEFAULT 0,
                    segment TEXT DEFAULT 'new',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS managers (
                    id SERIAL PRIMARY KEY,
                    tg_id BIGINT UNIQUE NOT NULL,
                    username TEXT,
                    name TEXT,
                    ref_code TEXT UNIQUE,
                    is_active INT DEFAULT 1,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS bookings (
                    id SERIAL PRIMARY KEY,
                    client_tg_id BIGINT,
                    client_username TEXT,
                    model_id INT,
                    model_name TEXT,
                    duration TEXT,
                    price INT,
                    payment_method TEXT,
                    contact_method TEXT DEFAULT 'bot',
                    status TEXT DEFAULT 'pending',
                    manager_id BIGINT DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS reviews (
                    id SERIAL PRIMARY KEY,
                    model_id INT,
                    client_name TEXT,
                    rating INT,
                    text TEXT,
                    is_verified INT DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS cities (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    is_active INT DEFAULT 1,
                    manager_id BIGINT DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS logs (
                    id SERIAL PRIMARY KEY,
                    tg_id BIGINT,
                    action TEXT,
                    details TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_models_manager_active ON models(manager_id, is_active);
                CREATE INDEX IF NOT EXISTS idx_bookings_manager ON bookings(manager_id);
                CREATE INDEX IF NOT EXISTS idx_clients_manager ON clients(manager_id);
            """)
            for c in ["Москва", "Санкт-Петербург", "Дубай", "Алматы", "Астана", "Екатеринбург"]:
                cur.execute(
                    "INSERT INTO cities (name, manager_id) VALUES (%s, 0) ON CONFLICT DO NOTHING", (c,)
                )

# ═══════════════════════════════════════════
# ASYNC POOL (для Aiogram)
# ═══════════════════════════════════════════
_async_pool: asyncpg.Pool | None = None

async def get_async_pool() -> asyncpg.Pool:
    global _async_pool
    if _async_pool is None:
        _async_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    return _async_pool

async def close_async_pool():
    global _async_pool
    if _async_pool:
        await _async_pool.close()
        _async_pool = None

async def db_fetch(query: str, *args):
    pool = await get_async_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)

async def db_fetchrow(query: str, *args):
    pool = await get_async_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)

async def db_execute(query: str, *args):
    pool = await get_async_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)

async def db_fetchval(query: str, *args):
    pool = await get_async_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)
