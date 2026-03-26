#!/bin/bash
set -e

export PYTHONPATH=/app:$PYTHONPATH

echo "=== Hopper Shopper Bot ==="

# Clear old alembic version tracking if it exists (from the old backend)
# The new bot uses its own migration chain
echo "Checking for old migration state..."
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from bot.config import settings

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
        if row and row[0] != '001_initial_bot':
            print(f'  Found old migration: {row[0]} — resetting...')
            await conn.execute(
                __import__('sqlalchemy').text('DELETE FROM alembic_version')
            )
            print('  Old migration state cleared.')
        elif row:
            print(f'  Migration already at: {row[0]}')
        else:
            print('  No existing migration state.')
    await engine.dispose()

try:
    asyncio.run(reset_alembic())
except Exception as e:
    print(f'  No alembic_version table yet (fresh DB): {e}')
" 2>/dev/null || echo "  Fresh database — no migration state to clear."

echo "Running database migrations..."
alembic upgrade head

echo "Starting Hopper Shopper bot..."
exec python -m bot.main
