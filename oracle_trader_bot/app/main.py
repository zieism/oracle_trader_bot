import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import os
from logging.handlers import RotatingFileHandler
import sys
from fastui import prebuilt_html
import aiohttp
from app.core.config import settings
from app.db.lazy_session import get_async_engine, get_session_factory, test_db_connection
from app.db.session import Base
from app.models import trade, bot_settings
from app.api.endpoints import trades as trades_router
from app.api.endpoints import exchange_info as exchange_info_router
from app.api.endpoints import market_data as market_data_router
from app.api.endpoints import strategy_signals as strategy_signals_router
from app.api.endpoints import trading as trading_router
from app.api.endpoints import order_management as order_management_router
from app.api.endpoints import bot_settings_api as bot_settings_router
from app.api.endpoints import frontend_fastui as frontend_fastui_router
from app.api.endpoints import bot_management_api as bot_management_router
from app.api.endpoints import server_logs_api as server_logs_router
from app.api.endpoints import analysis_logs_websocket as analysis_logs_router
from app.api.endpoints import health as health_router
os.makedirs(settings.LOG_DIR, exist_ok=True)
api_server_log_path = os.path.join(settings.LOG_DIR, settings.
    API_SERVER_LOG_FILE)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
if root_logger.hasHandlers():
    root_logger.handlers.clear()
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] %(message)s'
    , datefmt='%Y-%m-%d %H:%M:%S'))
root_logger.addHandler(console_handler)
file_handler = RotatingFileHandler(api_server_log_path, maxBytes=settings.
    MAX_LOG_FILE_SIZE_MB * 1024 * 1024, backupCount=settings.
    LOG_FILE_BACKUP_COUNT)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] %(message)s'
    , datefmt='%Y-%m-%d %H:%M:%S'))
root_logger.addHandler(file_handler)
uvicorn_access_logger = logging.getLogger('uvicorn.access')
uvicorn_access_logger.addHandler(file_handler)
uvicorn_access_logger.propagate = False
uvicorn_error_logger = logging.getLogger('uvicorn.error')
uvicorn_error_logger.addHandler(file_handler)
uvicorn_error_logger.propagate = False
logger = logging.getLogger(__name__)
from app.services.kucoin_futures_client import KucoinFuturesClient


async def create_db_and_tables():
    """Enhanced DB initialization with lite mode support"""
    startup_mode = getattr(settings, 'APP_STARTUP_MODE', 'full').lower()
    
    if startup_mode == 'lite':
        logger.info('Skipping DB table creation in lite mode')
        return False
    
    try:
        async_engine = get_async_engine()
        if not async_engine:
            logger.warning('No database engine available, skipping table creation')
            return False
            
        # Test connection first
        db_available = await test_db_connection()
        if not db_available:
            logger.warning('Database connection not available, skipping table creation')
            return False
            
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info('Database tables checked/created.')
        return True
    except Exception as e:
        logger.error(f'Error creating database tables: {e}', exc_info=True)
        if startup_mode == 'full':
            raise  # Re-raise in full mode
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Enhanced lifespan for DB-optional startup with lite/full modes"""
    startup_mode = getattr(settings, 'APP_STARTUP_MODE', 'full').lower()
    skip_db_init = getattr(settings, 'SKIP_DB_INIT', False)
    
    logger.info(f'Application startup sequence initiated in {startup_mode} mode...')
    logger.info(f'Skip DB initialization: {skip_db_init}')
    
    # Initialize global aiohttp session
    app.state.global_aiohttp_session = aiohttp.ClientSession()
    logger.info('Global aiohttp.ClientSession created and stored in app.state.')
    
    # Initialize KuCoin client
    try:
        app.state.kucoin_client = KucoinFuturesClient(external_session=app.state.global_aiohttp_session)
        logger.info('KucoinFuturesClient initialized and stored in app.state.')
        if hasattr(app.state.kucoin_client, '_ensure_markets_loaded'):
            await app.state.kucoin_client._ensure_markets_loaded()
            logger.info('Attempted to load markets for Kucoin client at startup.')
    except Exception as e:
        logger.error(f'Failed to initialize or load markets for KucoinFuturesClient: {e}', exc_info=True)
        app.state.kucoin_client = None
    
    # Initialize database with lite mode support
    db_initialized = False
    if not skip_db_init:
        try:
            logger.info('Initializing database tables via lifespan...')
            db_initialized = await create_db_and_tables()
            
            if db_initialized:
                # Ensure default bot settings
                try:
                    session_factory = get_session_factory()
                    if session_factory:
                        from app.crud import crud_bot_settings
                        async with session_factory() as db:
                            await crud_bot_settings.get_bot_settings(db)
                        logger.info('Default bot settings ensured in DB.')
                except Exception as e:
                    logger.error(f'Failed to ensure bot settings: {e}', exc_info=True)
                    if startup_mode == 'full':
                        raise
            else:
                logger.warning('Database not initialized, running in lite mode')
                
        except Exception as e:
            logger.error(f'!!! CRITICAL FAILURE DURING STARTUP (DB Initialization) !!!: {e}', exc_info=True)
            if startup_mode == 'full':
                raise
            logger.warning('Continuing in lite mode due to database failure')
    else:
        logger.info('Database initialization skipped by configuration')
    
    # Store startup state
    app.state.db_initialized = db_initialized
    app.state.startup_mode = startup_mode
    
    logger.info('FastUI model rebuild is handled within its respective module.')
    logger.info(f'Application startup complete (db_initialized={db_initialized}, mode={startup_mode})')
    
    yield
    
    # Shutdown sequence
    logger.info('Application shutdown sequence initiated...')
    
    # Stop bot engine if running
    from app.core import bot_process_manager
    status_str, pid = bot_process_manager.get_bot_process_status()
    if status_str == 'running' and pid is not None:
        logger.info(f'FastAPI shutdown: Attempting to stop running bot engine (PID: {pid})...')
        success, message = bot_process_manager.stop_bot_engine()
        if not success:
            logger.error(f'FastAPI shutdown: Failed to gracefully stop bot engine: {message}')
    
    # Close KuCoin client
    if hasattr(app.state, 'kucoin_client') and app.state.kucoin_client:
        if hasattr(app.state.kucoin_client, 'close_session') and callable(app.state.kucoin_client.close_session):
            try:
                await app.state.kucoin_client.close_session()
                logger.info('Kucoin client custom session closed during FastAPI shutdown.')
            except Exception as e:
                logger.error(f'Error closing Kucoin client custom session during FastAPI shutdown: {e}', exc_info=True)
        
        if hasattr(app.state.kucoin_client.exchange, 'close') and callable(app.state.kucoin_client.exchange.close):
            try:
                await app.state.kucoin_client.exchange.close()
                logger.info('Underlying ccxt exchange instance closed during FastAPI shutdown.')
            except Exception as e:
                logger.error(f'Error closing underlying ccxt exchange instance during FastAPI shutdown: {e}', exc_info=True)
    
    # Close global aiohttp session
    if (hasattr(app.state, 'global_aiohttp_session') and app.state.global_aiohttp_session 
        and not app.state.global_aiohttp_session.closed):
        try:
            await app.state.global_aiohttp_session.close()
            logger.info('Global aiohttp.ClientSession closed.')
        except Exception as e:
            logger.error(f'Error closing global aiohttp session during FastAPI shutdown: {e}', exc_info=True)
    
    # Dispose database engine if initialized
    if db_initialized:
        try:
            async_engine = get_async_engine()
            if async_engine and hasattr(async_engine, 'dispose') and callable(async_engine.dispose):
                await async_engine.dispose()
                logger.info('Database connection pool closed.')
        except Exception as e:
            logger.error(f'Error disposing database engine during FastAPI shutdown: {e}', exc_info=True)
    
    logger.info('Application shutdown complete.')


app = FastAPI(
    title=settings.PROJECT_NAME, 
    description='API for the Automated KuCoin Futures Trading Bot with DB-Optional Startup',
    version=settings.VERSION,
    lifespan=lifespan
)
SERVER_PUBLIC_IP = '150.241.85.30'
origins = ['http://localhost', 'http://localhost:5173',
    'http://localhost:3000', 'http://localhost:8080',
    'http://localhost:4173', f'http://{SERVER_PUBLIC_IP}:5173',
    f'http://{SERVER_PUBLIC_IP}', f'http://{SERVER_PUBLIC_IP}:5174',
    f'http://{SERVER_PUBLIC_IP}:3000', f'https://{SERVER_PUBLIC_IP}',
    'https://localhost:5173', 'http://127.0.0.1:5173', 'http://127.0.0.1:3000']
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials
    =True, allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS',
    'PATCH'], allow_headers=['*'], expose_headers=['*'])
app.include_router(trades_router.router, prefix='/api/v1/db/trades', tags=[
    'Database - Trades'])
app.include_router(exchange_info_router.router, prefix='/api/v1/exchange',
    tags=['Exchange Info'])
app.include_router(market_data_router.router, prefix='/api/v1/market', tags
    =['Market Data & Indicators'])
app.include_router(strategy_signals_router.router, prefix='/api/v1/signals',
    tags=['Strategy Signals'])
app.include_router(trading_router.router, prefix='/api/v1/trading', tags=[
    'Trading Execution'])
app.include_router(order_management_router.router, prefix='/api/v1/orders',
    tags=['Order & Position Management'])
app.include_router(bot_settings_router.router, prefix=
    '/api/v1/bot-settings', tags=['Bot Settings'])
app.include_router(frontend_fastui_router.router, prefix='/api/ui', tags=[
    'Frontend UI Components'])
app.include_router(bot_management_router.router, prefix=
    '/api/v1/bot-management', tags=['Bot Management'])
app.include_router(server_logs_router.router, prefix='/api/v1/logs', tags=[
    'Server Logs'])
app.include_router(analysis_logs_router.router, prefix='/api/v1', tags=[
    'Analysis Logs (WebSocket)'])
app.include_router(health_router.router, prefix='/api/v1/health', tags=[
    'Health Monitoring'])


@app.get('/', include_in_schema=False, response_class=HTMLResponse)
@app.get('/ui', include_in_schema=False, response_class=HTMLResponse)
@app.get('/ui/{path:path}', include_in_schema=False, response_class=HTMLResponse)
async def serve_fastui_html_shell(path: str = ""):
    """Serve FastUI HTML shell for frontend UI paths only."""
    return HTMLResponse(prebuilt_html(title=f'{settings.PROJECT_NAME} UI',
        api_root_url='/api/ui'))
