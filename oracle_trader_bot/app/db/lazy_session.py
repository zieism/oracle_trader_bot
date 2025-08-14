"""
Database module with lazy initialization and lite mode support.

This module provides:
- Lazy engine/session factory that connects on first use
- Lite mode support (DB optional)
- Global state management for DB availability
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Optional, AsyncGenerator
import asyncio
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global state
_async_engine: Optional[AsyncEngine] = None
_session_factory: Optional[sessionmaker] = None
_db_unavailable: bool = False
_db_checked: bool = False

# Base class for declarative class definitions
Base = declarative_base()


def get_db_status() -> dict:
    """Get current database status."""
    return {
        "available": not _db_unavailable,
        "checked": _db_checked,
        "lite_mode": settings.SKIP_DB_INIT,
        "startup_mode": settings.APP_STARTUP_MODE
    }


async def get_async_engine() -> Optional[AsyncEngine]:
    """
    Lazy factory for async engine.
    Returns None if in lite mode and DB is unavailable.
    """
    global _async_engine, _db_unavailable, _db_checked
    
    if _async_engine is not None:
        return _async_engine
        
    if settings.SKIP_DB_INIT and _db_unavailable:
        logger.warning("Database unavailable and in lite mode - returning None engine")
        return None
    
    try:
        logger.info(f"Creating async engine for {settings.ASYNC_DATABASE_URL}")
        _async_engine = create_async_engine(
            settings.ASYNC_DATABASE_URL,
            pool_recycle=3600,
            pool_pre_ping=True,
            # Reduce timeout for lite mode
            pool_timeout=5 if settings.SKIP_DB_INIT else 30,
        )
        
        # Test connection
        async with _async_engine.begin() as conn:
            await conn.execute("SELECT 1")
            
        _db_unavailable = False
        _db_checked = True
        logger.info("Database connection established successfully")
        return _async_engine
        
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        _db_unavailable = True
        _db_checked = True
        
        if settings.SKIP_DB_INIT:
            logger.warning("Database unavailable but continuing in lite mode")
            return None
        else:
            logger.error("Database required in full mode - raising exception")
            raise


async def get_session_factory() -> Optional[sessionmaker]:
    """
    Lazy factory for session maker.
    Returns None if in lite mode and DB is unavailable.
    """
    global _session_factory
    
    if _session_factory is not None:
        return _session_factory
        
    engine = await get_async_engine()
    if engine is None:
        return None
        
    _session_factory = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    return _session_factory


async def get_db_session() -> AsyncGenerator[Optional[AsyncSession], None]:
    """
    FastAPI dependency that provides a SQLAlchemy AsyncSession.
    Yields None if database is unavailable in lite mode.
    """
    session_factory = await get_session_factory()
    
    if session_factory is None:
        logger.warning("No session factory available - yielding None")
        yield None
        return
    
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db_tables() -> bool:
    """
    Initialize database tables.
    Returns True if successful, False if failed in lite mode.
    """
    if settings.SKIP_DB_INIT:
        logger.info("Skipping DB initialization in lite mode")
        return False
        
    try:
        engine = await get_async_engine()
        if engine is None:
            return False
            
        # Import all models to register them with Base.metadata
        from app.models import trade, bot_settings
        
        async with engine.begin() as conn:
            logger.info("Creating database tables if they don't exist...")
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database tables initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        if not settings.SKIP_DB_INIT:
            raise
        return False


async def test_db_connection() -> tuple[bool, Optional[str]]:
    """
    Test database connection.
    Returns (success: bool, error_message: Optional[str])
    """
    try:
        engine = await get_async_engine()
        if engine is None:
            return False, "Database engine not available"
            
        async with engine.begin() as conn:
            await conn.execute("SELECT 1 as health_check")
            
        return True, None
        
    except Exception as e:
        error_msg = f"Database connection failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


async def close_db_connections():
    """Close all database connections."""
    global _async_engine, _session_factory
    
    if _async_engine:
        logger.info("Closing database engine")
        await _async_engine.dispose()
        _async_engine = None
        _session_factory = None
