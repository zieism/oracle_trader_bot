# app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings # Import your settings

# Use the ASYNC_DATABASE_URL from your config
SQLALCHEMY_DATABASE_URL = settings.ASYNC_DATABASE_URL

# Create an asynchronous SQLAlchemy engine
async_engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    # echo=True,  # Useful for debugging SQL queries, set to False in production
    pool_recycle=3600, # Recycle connections every hour
    pool_pre_ping=True # Check connection health
)

# Create a session factory for creating AsyncSession instances
# This is your "SessionLocal" equivalent
AsyncSessionFactory = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for declarative class definitions (our database models)
Base = declarative_base()

# Dependency to get a DB session in FastAPI path operations
async def get_db_session() -> AsyncSession: # Changed type hint for generator if using yield
    """
    FastAPI dependency that provides a SQLAlchemy AsyncSession.
    Ensures the session is closed after the request is finished.
    """
    # logger = logging.getLogger(__name__) # If you want logging within this function
    # logger.debug("Creating DB session")
    async with AsyncSessionFactory() as session:
        try:
            yield session
            # logger.debug("DB session commiting")
            await session.commit() 
        except Exception:
            # logger.error("DB session rolling back due to exception", exc_info=True)
            await session.rollback() 
            raise
        # finally:
            # logger.debug("DB session closing")
            # The 'async with' statement handles closing the session automatically.
            # await session.close() # Not strictly necessary due to 'async with'
    # logger.debug("DB session closed and released")


# --- New function to initialize database tables ---
async def init_db():
    """
    Initializes the database by creating all tables defined by Base.metadata.
    This should be called once at application startup (e.g., in main.py lifespan or bot_engine.py).
    """
    # Import all models here before calling create_all!
    # This ensures Base.metadata is aware of all tables.
    from app.models import trade # Or import all models from a central models.__init__

    async with async_engine.begin() as conn:
        # print("Attempting to drop all tables (DEBUG ONLY - REMOVE FOR PRODUCTION)")
        # await conn.run_sync(Base.metadata.drop_all) # CAUTION: DELETES ALL DATA
        print("Attempting to create all tables if they don't exist...")
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables checked/created.")