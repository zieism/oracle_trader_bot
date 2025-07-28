# app/crud/crud_bot_settings.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional

from app.models.bot_settings import BotSettings as BotSettingsModel, TradeAmountMode
from app.schemas.bot_settings import BotSettingsCreate, BotSettingsUpdate
from app.core.config import settings as global_app_settings # For default values

# We assume a single row of settings with a fixed ID, e.g., 1
BOT_SETTINGS_ID = 1

async def get_bot_settings(db: AsyncSession) -> Optional[BotSettingsModel]:
    """
    Retrieves the bot settings. If not found, creates them with default values.
    """
    result = await db.execute(
        select(BotSettingsModel).filter(BotSettingsModel.id == BOT_SETTINGS_ID)
    )
    db_settings = result.scalar_one_or_none()

    if db_settings is None:
        print(f"No bot settings found in DB with ID {BOT_SETTINGS_ID}, creating with defaults.")
        # Create with defaults from the global app settings or Pydantic model defaults
        default_settings_data = BotSettingsCreate(
            max_concurrent_trades=global_app_settings.MAX_CONCURRENT_TRADES_BOT_CONFIG if hasattr(global_app_settings, 'MAX_CONCURRENT_TRADES_BOT_CONFIG') else 3, # Example
            trade_amount_mode=TradeAmountMode.FIXED_USD, # Default mode
            fixed_trade_amount_usd=global_app_settings.FIXED_USD_AMOUNT_PER_TRADE, # From global settings
            percentage_trade_amount=global_app_settings.PERCENTAGE_TRADE_AMOUNT_BOT_CONFIG if hasattr(global_app_settings, 'PERCENTAGE_TRADE_AMOUNT_BOT_CONFIG') else 1.0, # Example
            daily_loss_limit_percentage=global_app_settings.DAILY_LOSS_LIMIT_PERCENTAGE_BOT_CONFIG if hasattr(global_app_settings, 'DAILY_LOSS_LIMIT_PERCENTAGE_BOT_CONFIG') else None # Example
        )
        # Ensure all fields in BotSettingsModel are covered by BotSettingsCreate defaults
        # or explicitly set here if BotSettingsCreate doesn't have them all with defaults.
        # The BotSettingsBase (parent of BotSettingsCreate) has defaults for most.

        db_settings = BotSettingsModel(id=BOT_SETTINGS_ID, **default_settings_data.model_dump())
        db.add(db_settings)
        try:
            await db.commit()
            await db.refresh(db_settings)
            print(f"Default bot settings created with ID {BOT_SETTINGS_ID}.")
        except Exception as e:
            await db.rollback()
            print(f"Error creating default bot settings: {e}")
            return None # Or raise
    return db_settings

async def update_bot_settings(
    db: AsyncSession, 
    settings_update: BotSettingsUpdate
) -> Optional[BotSettingsModel]:
    """
    Updates existing bot settings.
    """
    db_settings = await get_bot_settings(db) # Get existing or create if not found
    if not db_settings:
        # This case should ideally be handled if get_bot_settings can return None on creation error
        print("Error: Bot settings could not be fetched or created for update.")
        return None

    update_data = settings_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if hasattr(db_settings, key):
            # Handle Enum conversion if necessary
            if key == "trade_amount_mode" and isinstance(value, TradeAmountMode):
                setattr(db_settings, key, value.value)
            else:
                setattr(db_settings, key, value)

    db.add(db_settings) # Mark as dirty
    try:
        await db.commit()
        await db.refresh(db_settings)
        print(f"Bot settings (ID: {BOT_SETTINGS_ID}) updated successfully.")
        return db_settings
    except Exception as e:
        await db.rollback()
        print(f"Error updating bot settings: {e}")
        return None # Or raise