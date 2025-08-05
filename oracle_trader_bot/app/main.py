# app/main.py
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
from sqlalchemy.sql import text 

from app.core.config import settings
from app.db.session import async_engine, Base 
from app.models import trade, bot_settings 

# Import API routers
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
from app.api.endpoints import analysis_logs_websocket as analysis_logs_router # ADDED: Import new analysis logs websocket router
from app.api.endpoints import phase3_monitoring as phase3_monitoring_router # ADDED: Import new Phase 3 monitoring router

# --- Configure logging for FastAPI server to file and console ---
# Ensure log directory exists
os.makedirs(settings.LOG_DIR, exist_ok=True)
api_server_log_path = os.path.join(settings.LOG_DIR, settings.API_SERVER_LOG_FILE)

# Get the root logger for general application logging
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Clear existing handlers to prevent duplicate output if reloaded (e.g., by uvicorn reload)
if root_logger.hasHandlers():
    root_logger.handlers.clear()

# Console Handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
root_logger.addHandler(console_handler)

# File Handler for API server logs
file_handler = RotatingFileHandler(
    api_server_log_path,
    maxBytes=settings.MAX_LOG_FILE_SIZE_MB * 1024 * 1024, 
    backupCount=settings.LOG_FILE_BACKUP_COUNT
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
root_logger.addHandler(file_handler)

# Additionally, configure uvicorn loggers to use our file handler
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.addHandler(file_handler)
uvicorn_access_logger.propagate = False 

uvicorn_error_logger = logging.getLogger("uvicorn.error")
uvicorn_error_logger.addHandler(file_handler)
uvicorn_error_logger.propagate = False

logger = logging.getLogger(__name__) 
# --- End logging configuration ---

from app.exchange_clients.kucoin_futures_client import KucoinFuturesClient 

async def create_db_and_tables():
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables checked/created.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}", exc_info=True)
        raise 

@asynccontextmanager
async def lifespan(app: FastAPI): 
    logger.info("Application startup sequence initiated...")
    app.state.global_aiohttp_session = aiohttp.ClientSession() 
    logger.info("Global aiohttp.ClientSession created and stored in app.state.")
    try:
        app.state.kucoin_client = KucoinFuturesClient(external_session=app.state.global_aiohttp_session)
        logger.info("KucoinFuturesClient initialized and stored in app.state.")
        if hasattr(app.state.kucoin_client, '_ensure_markets_loaded'):
            await app.state.kucoin_client._ensure_markets_loaded()
            logger.info("Attempted to load markets for Kucoin client at startup.")
    except Exception as e:
        logger.error(f"Failed to initialize or load markets for KucoinFuturesClient: {e}", exc_info=True)
        app.state.kucoin_client = None 
    try:
        logger.info("Initializing database tables via lifespan...")
        await create_db_and_tables()
        from app.db.session import AsyncSessionFactory
        from app.crud import crud_bot_settings
        async with AsyncSessionFactory() as db:
           await crud_bot_settings.get_bot_settings(db) 
        logger.info("Default bot settings ensured in DB.")
    except Exception as e:
        logger.error(f"!!! CRITICAL FAILURE DURING STARTUP (DB Initialization) !!!: {e}", exc_info=True)
    
    logger.info("FastUI model rebuild is handled within its respective module.")

    logger.info("Application startup complete.")
    yield 
    
    logger.info("Application shutdown sequence initiated...")
    from app.core import bot_process_manager 
    status_str, pid = bot_process_manager.get_bot_process_status()
    if status_str == "running" and pid is not None:
        logger.info(f"FastAPI shutdown: Attempting to stop running bot engine (PID: {pid})...")
        success, message = bot_process_manager.stop_bot_engine()
        if not success:
            logger.error(f"FastAPI shutdown: Failed to gracefully stop bot engine: {message}")

    if hasattr(app.state, 'kucoin_client') and app.state.kucoin_client:
        if hasattr(app.state.kucoin_client, 'close_session') and callable(app.state.kucoin_client.close_session):
            try:
                await app.state.kucoin_client.close_session() 
                logger.info("Kucoin client custom session closed during FastAPI shutdown.")
            except Exception as e:
                logger.error(f"Error closing Kucoin client custom session during FastAPI shutdown: {e}", exc_info=True)
        
        if hasattr(app.state.kucoin_client.exchange, 'close') and callable(app.state.kucoin_client.exchange.close):
            try:
                await app.state.kucoin_client.exchange.close()
                logger.info("Underlying ccxt exchange instance closed during FastAPI shutdown.")
            except Exception as e:
                logger.error(f"Error closing underlying ccxt exchange instance during FastAPI shutdown: {e}", exc_info=True)

    if hasattr(app.state, 'global_aiohttp_session') and app.state.global_aiohttp_session and \
       not app.state.global_aiohttp_session.closed:
        try:
            await app.state.global_aiohttp_session.close()
            logger.info("Global aiohttp.ClientSession closed.")
        except Exception as e:
            logger.error(f"Error closing global aiohttp session during FastAPI shutdown: {e}", exc_info=True)

    if hasattr(async_engine, 'dispose') and callable(async_engine.dispose):
        try:
            await async_engine.dispose()
            logger.info("Database connection pool closed.")
        except Exception as e:
            logger.error(f"Error disposing database engine during FastAPI shutdown: {e}", exc_info=True)
    logger.info("Application shutdown complete.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for the Automated KuCoin Futures Trading Bot",
    version="0.1.14_websocket_prep", # Incremented version
    lifespan=lifespan 
)

SERVER_PUBLIC_IP = "150.241.85.30" 
origins = [
    "http://localhost", "http://localhost:5173", "http://localhost:3000", 
    f"http://{SERVER_PUBLIC_IP}:5173", f"http://{SERVER_PUBLIC_IP}",
    f"http://{SERVER_PUBLIC_IP}:5174", 
]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True, 
    allow_methods=["*"], allow_headers=["*"],
)

app.include_router(trades_router.router, prefix="/api/v1/db/trades", tags=["Database - Trades"]) 
app.include_router(exchange_info_router.router, prefix="/api/v1/exchange", tags=["Exchange Info"]) 
app.include_router(market_data_router.router, prefix="/api/v1/market", tags=["Market Data & Indicators"]) 
app.include_router(strategy_signals_router.router, prefix="/api/v1/signals", tags=["Strategy Signals"])
app.include_router(trading_router.router, prefix="/api/v1/trading", tags=["Trading Execution"])
app.include_router(order_management_router.router, prefix="/api/v1/orders", tags=["Order & Position Management"]) 
app.include_router(bot_settings_router.router, prefix="/api/v1/bot-settings", tags=["Bot Settings"])
app.include_router(frontend_fastui_router.router, prefix="/api/ui", tags=["Frontend UI Components"])
app.include_router(bot_management_router.router, prefix="/api/v1/bot-management", tags=["Bot Management"])
app.include_router(server_logs_router.router, prefix="/api/v1/logs", tags=["Server Logs"]) 
app.include_router(analysis_logs_router.router, prefix="/api/v1", tags=["Analysis Logs (WebSocket)"]) # ADDED: Include new analysis logs router
app.include_router(phase3_monitoring_router.router, prefix="/api/v1/phase3", tags=["Phase 3 Monitoring & Management"]) # ADDED: Include Phase 3 monitoring router


@app.get("/{path:path}", include_in_schema=False) 
async def serve_fastui_html_shell(path: str): 
    return HTMLResponse(prebuilt_html(title=f"{settings.PROJECT_NAME} UI", api_root_url="/api/ui"))

@app.get("/api/health", tags=["Health Check"]) 
async def health_check() -> Dict[str, str]:
    kucoin_client_status = "initialized" if hasattr(app.state, 'kucoin_client') and app.state.kucoin_client else "not_initialized"
    db_status = "unknown"
    try:
        async with async_engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    from app.core import bot_process_manager 
    engine_status_str, _ = bot_process_manager.get_bot_process_status()

    return {
        "status": "healthy", "message": "API is operational.", "project_name": settings.PROJECT_NAME,
        "version": app.version, "debug_mode": settings.DEBUG,
        "kucoin_client_status": kucoin_client_status, "database_status": db_status,
        "bot_engine_status": engine_status_str
    }
