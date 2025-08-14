import asyncio
import aiohttp

async def test_health_endpoints():
    async with aiohttp.ClientSession() as session:
        # Test app health
        import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'oracle_trader_bot'))

from app.core.config import settings
import asyncio
import aiohttp

async def test_api():
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{settings.API_INTERNAL_BASE_URL}/api/v1/health/app') as r:
            print(f'App Health - Status: {r.status}')
            print(f'App Health - Content: {await r.text()}\n')
            
        # Test exchange health
        async with session.get(f'{settings.API_INTERNAL_BASE_URL}/api/v1/health/exchange') as r:
            print(f'Exchange Health - Status: {r.status}')
            print(f'Exchange Health - Content: {await r.text()}\n')

if __name__ == "__main__":
    asyncio.run(test_health_endpoints())
