#!/bin/bash
set -e

export PYTHONPATH=/app:$PYTHONPATH

echo "=== Hopper Shopper Bot ==="

# ── Wait for database to be ready ────────────────────────────────
MAX_RETRIES=30
RETRY_INTERVAL=2

echo "Waiting for database to be ready..."
for i in $(seq 1 $MAX_RETRIES); do
    if python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from bot.config import settings

async def check():
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        await conn.execute(__import__('sqlalchemy').text('SELECT 1'))
    await engine.dispose()

asyncio.run(check())
" 2>/dev/null; then
        echo "  Database is ready!"
        break
    fi

    if [ "$i" -eq "$MAX_RETRIES" ]; then
        echo "  ERROR: Database not ready after $MAX_RETRIES attempts. Exiting."
        exit 1
    fi

    echo "  Attempt $i/$MAX_RETRIES — database not ready, retrying in ${RETRY_INTERVAL}s..."
    sleep $RETRY_INTERVAL
done

# ── Clear old alembic version tracking if needed ─────────────────
# Only reset if the revision is NOT part of our bot migration chain.
BOT_REVISIONS="001_initial_bot 002_add_detail 003_add_qty_brand 004_unique_constraints"

echo "Checking for old migration state..."
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from bot.config import settings

BOT_REVISIONS = set('$BOT_REVISIONS'.split())

async def reset_alembic():
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        # Check if alembic_version exists and has old revisions
        result = await conn.execute(
            __import__('sqlalchemy').text(
                \"SELECT version_num FROM alembic_version LIMIT 1\"
            )
        )
        row = result.fetchone()
        if row and row[0] not in BOT_REVISIONS:
            print(f'  Found old (non-bot) migration: {row[0]} — resetting...')
            await conn.execute(
                __import__('sqlalchemy').text('DELETE FROM alembic_version')
            )
            print('  Old migration state cleared.')
        elif row:
            print(f'  Migration already at: {row[0]} (valid)')
        else:
            print('  No existing migration state.')
    await engine.dispose()

try:
    asyncio.run(reset_alembic())
except Exception as e:
    print(f'  No alembic_version table yet (fresh DB): {e}')
" || echo "  Fresh database — no migration state to clear."

echo "Running database migrations..."
alembic upgrade head

echo "Starting Hopper Shopper bot..."
# Brief pause to let Telegram release any previous polling session
# (the bot's own pre-startup code also force-closes stale sessions)
sleep 2
exec python -m bot.main
