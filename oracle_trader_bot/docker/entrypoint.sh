#!/bin/bash
set -e

echo "Starting Oracle Trader Bot (Fixed Version)..."

# Wait for PostgreSQL using basic network test
echo "Waiting for PostgreSQL..."
for i in {1..30}; do
    if timeout 3 bash -c 'cat < /dev/null > /dev/tcp/postgres/5432'; then
        echo "PostgreSQL is ready!"
        break
    fi
    
    if [ $i -eq 30 ]; then
        echo "PostgreSQL connection timeout"
        exit 1
    fi
    
    echo "PostgreSQL not ready, waiting... (attempt $i/30)"
    sleep 2
done

# Wait for Redis
echo "Waiting for Redis..."
for i in {1..10}; do
    if timeout 3 bash -c 'cat < /dev/null > /dev/tcp/redis/6379'; then
        echo "Redis is ready!"
        break
    fi
    sleep 1
done

echo "All services ready. Starting application..."
echo "Command: $@"
exec "$@"
