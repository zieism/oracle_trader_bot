# app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from app.core.config import settings
import logging
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Global state for DB availability
_db_available: bool = True
_db_error_message: Optional[str] = None
_async_engine: Optional[create_async_engine] = None
_session_factory: Optional[sessionmaker] = None

# Base class for declarative class definitions (our database models)
Base = declarative_base()

def get_engine():
    """Lazy factory for database engine."""
    global _async_engine, _db_available, _db_error_message
    
    if _async_engine is None:
        try:
            SQLALCHEMY_DATABASE_URL = settings.ASYNC_DATABASE_URL
            _async_engine = create_async_engine(
                SQLALCHEMY_DATABASE_URL,
                pool_recycle=3600,
                pool_pre_ping=True,
                echo=settings.DEBUG
            )
            logger.info("Database engine created successfully")
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            _db_available = False
            _db_error_message = str(e)
            
    return _async_engine

def get_session_factory():
    """Lazy factory for session maker."""
    global _session_factory
    
    if _session_factory is None:
        engine = get_engine()
        if engine:
            _session_factory = sessionmaker(
                bind=engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
        
    return _session_factory

async def check_db_connection() -> tuple[bool, Optional[str]]:
    """Check database connection health."""
    global _db_available, _db_error_message
    
    try:
        engine = get_engine()
        if not engine:
            return False, _db_error_message
            
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        _db_available = True
        _db_error_message = None
        return True, None
        
    except Exception as e:
        _db_available = False
        _db_error_message = str(e)
        logger.error(f"Database connection check failed: {e}")
        return False, str(e)

def is_db_available() -> bool:
    """Check if database is available."""
    return _db_available

def get_db_error() -> Optional[str]:
    """Get the last database error message."""
    return _db_error_message

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a SQLAlchemy AsyncSession.
    Raises HTTPException(503) if database is not available.
    """
    from fastapi import HTTPException
    
    if not _db_available:
        raise HTTPException(
            status_code=503,
            detail=f"Database temporarily unavailable: {_db_error_message}"
        )
    
    session_factory = get_session_factory()
    if not session_factory:
        raise HTTPException(
            status_code=503,
            detail="Database session factory not available"
        )
    
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise


async def init_db():
    """
    Initializes the database by creating all tables defined by Base.metadata.
    This should be called only in 'full' startup mode.
    """
    global _db_available, _db_error_message
    
    if settings.SKIP_DB_INIT:
        logger.info("Skipping database initialization (lite mode)")
        return
    
    try:
        # Import all models here before calling create_all
        from app.models import trade, bot_settings
        
        engine = get_engine()
        if not engine:
            raise Exception("Database engine not available")
            
        async with engine.begin() as conn:
            logger.info("Creating database tables if they don't exist...")
            await conn.run_sync(Base.metadata.create_all)
        
        _db_available = True
        _db_error_message = None
        logger.info("Database tables created successfully")
        
    except Exception as e:
        _db_available = False
        _db_error_message = str(e)
        logger.error(f"Database initialization failed: {e}")
        
        if not settings.SKIP_DB_INIT:
            # In full mode, this is a critical error
            raise
        
        # In lite mode, we just log and continue