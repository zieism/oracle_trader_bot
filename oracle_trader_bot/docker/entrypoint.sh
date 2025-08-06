#!/bin/bash
set -e

# Oracle Trader Bot Entrypoint Script
echo "Starting Oracle Trader Bot..."

# Set default values for environment variables
export ENVIRONMENT=${ENVIRONMENT:-development}
export POSTGRES_SERVER=${POSTGRES_SERVER:-localhost}
export POSTGRES_PORT=${POSTGRES_PORT:-5432}
export REDIS_URL=${REDIS_URL:-redis://localhost:6379}

# Wait for database to be ready
echo "Waiting for database connection..."
for i in {1..30}; do
    if python -c "
import asyncpg
import asyncio
from app.core.config import settings

async def check_db():
    try:
        conn = await asyncpg.connect(settings.ASYNC_DATABASE_URL)
        await conn.close()
        print('Database connection successful')
        return True
    except Exception as e:
        print(f'Database connection failed: {e}')
        return False

if asyncio.run(check_db()):
    exit(0)
else:
    exit(1)
"; then
        echo "Database is ready!"
        break
    fi
    
    if [ $i -eq 30 ]; then
        echo "Database connection timeout after 30 attempts"
        exit 1
    fi
    
    echo "Database not ready, waiting... (attempt $i/30)"
    sleep 2
done

# Run database migrations if needed
echo "Running database migrations..."
python -c "
import asyncio
from app.db.base import init_db

async def run_migrations():
    try:
        await init_db()
        print('Database migrations completed')
    except Exception as e:
        print(f'Migration failed: {e}')
        raise

asyncio.run(run_migrations())
"

# Start the application
echo "Starting application with command: $*"
exec "$@"