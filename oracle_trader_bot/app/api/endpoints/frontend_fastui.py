@router.get("/ui", response_model=FastUI, response_model_exclude_none=True)
async def fastui_dashboard_ui_api(
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client)
) -> FastUI:
    components = await fastui_dashboard_root_api(kucoin_client)
    return FastUI(components=components)
from fastapi import APIRouter, Depends, HTTPException
from fastui import FastUI, AnyComponent
from fastui import components as c
from fastui.components.display import DisplayMode, DisplayLookup
from fastui.events import GoToEvent
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import List, Optional, Dict
import logging

from app.api.dependencies import get_kucoin_client
from app.exchange_clients.kucoin_futures_client import KucoinFuturesClient
from app.db.session import get_db_session
from app.schemas.bot_settings import BotSettings as BotSettingsSchema
from app.crud import crud_bot_settings
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class AccountBalance(BaseModel):
    currency: str
    total: Optional[float] = None
    free: Optional[float] = None
    used: Optional[float] = None

class DashboardData(BaseModel):
    bot_status: str = "Initializing..."
    last_update: str
    account_overview: Optional[List[AccountBalance]] = None
    error_message: Optional[str] = None

@router.get("/ui", response_model=FastUI, response_model_exclude_none=True)
async def fastui_dashboard_ui_api(
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client),
    db: AsyncSession = Depends(get_db_session)
) -> FastUI:
    components = await fastui_dashboard_root_api(kucoin_client)
    # دریافت bot settings و افزودن به متادیتا
    try:
        settings = await crud_bot_settings.get_settings(db)
        if not settings:
            settings = BotSettingsSchema(
                symbols_to_trade=[],
                max_concurrent_trades=0,
                trade_amount_mode="",
                fixed_trade_amount_usd=0,
                percentage_trade_amount=0,
                daily_loss_limit_percentage=None,
                updated_at=None
            )
    except Exception as e:
        settings = None
    return FastUI(components=components, metadata={"bot_settings": settings.dict() if settings else {}})


    # Graceful error handling for Kucoin client and account overview
    if kucoin_client is None:
        dashboard_data.bot_status = "Error: KuCoin Client Unavailable"
        dashboard_data.error_message = "Exchange client not initialized. Check server startup logs."
        logger.critical("FastUI: KuCoin client is None in dashboard_root_api.")
    else:
        try:
            logger.debug("FastUI: Fetching account overview...")
            overview = await kucoin_client.get_account_overview()
            if overview:
                dashboard_data.bot_status = "Operational"
                balances_to_display = []
                logger.debug(f"FastUI: Raw account overview: {overview}")

                for currency_code in overview.keys():
                    if currency_code.upper() in ['INFO', 'TIMESTAMP', 'DATETIME', 'FREE', 'USED', 'TOTAL']:
                        continue

                    balance_info = overview.get(currency_code)
                    if isinstance(balance_info, dict) and 'total' in balance_info:
                        total_val = balance_info.get('total')
                        if currency_code == 'USDT' or (total_val is not None and total_val > 0):
                            balances_to_display.append(
                                AccountBalance(
                                    currency=currency_code,
                                    total=total_val,
                                    free=balance_info.get('free'),
                                    used=balance_info.get('used')
                                )
                            )
                dashboard_data.account_overview = sorted(balances_to_display, key=lambda b: b.currency)
                if not balances_to_display:
                    logger.info("FastUI: No significant balances found in account overview to display.")
                else:
                    logger.info(f"FastUI: Processed {len(balances_to_display)} balances for display.")
            else:
                dashboard_data.bot_status = "Warning: Could not fetch account overview."
                dashboard_data.error_message = "Failed to retrieve account balance from exchange."
                logger.warning(f"FastUI: Account overview fetch returned None or empty for dashboard.")
        except Exception as e:
            dashboard_data.bot_status = "Error Fetching Dashboard Data"
            dashboard_data.error_message = f"An unexpected error occurred: {str(e)}"
            logger.error("FastUI: Error in dashboard_root_api", exc_info=True)

    logger.debug(f"FastUI: Returning components for dashboard. Bot Status: {dashboard_data.bot_status}")
    return [
        c.PageTitle(text='Oracle Trader Bot - Dashboard'),
        c.Navbar(title='OracleBot', title_event=GoToEvent(url='/')),
        c.Page(components=[
            c.Heading(text='Bot Dashboard', level=2, class_name="mb-4"),
            c.Paragraph(text=f"Last Data Refresh: {dashboard_data.last_update}", class_name="text-sm text-muted-foreground"),
            c.Card(components=[
                c.Heading(text='Status', level=4),
                c.Paragraph(text=dashboard_data.bot_status),
                c.Paragraph(text=dashboard_data.error_message if dashboard_data.error_message else "", class_name="text-danger")
            ], class_name="mb-4 p-4 border rounded-lg"),
            c.Heading(text='Account Balances', level=3, class_name="my-4"),
            c.Table(
                data=dashboard_data.account_overview if dashboard_data.account_overview else [],
                columns=[
                    DisplayLookup(field='currency', title='Asset'),
                    DisplayLookup(field='free', title='Available', mode=DisplayMode.float, format="%.4f"),
                    DisplayLookup(field='used', title='In Orders', mode=DisplayMode.float, format="%.4f"),
                    DisplayLookup(field='total', title='Total', mode=DisplayMode.float, format="%.4f"),
                ],
                no_data_message="No balance data available or error fetching."
            ),
            c.Div(components=[
                c.Link(components=[c.Button(text='View Bot Settings', class_name="btn btn-primary mt-4")], on_click=GoToEvent(url='/bot-settings-view')),
                c.Link(components=[c.Button(text='View Trades Log', class_name="btn btn-secondary mt-4 ml-2")], on_click=GoToEvent(url='/trades-log')),
            ], class_name="mt-4")
        ]),
        c.Footer(extra_text=f"© {datetime.now(timezone.utc).year} Oracle Trader Bot", links=[])
    ]

# Rebuild Pydantic models to resolve any forward references
AccountBalance.model_rebuild()
DashboardData.model_rebuild()
FastUI.model_rebuild()