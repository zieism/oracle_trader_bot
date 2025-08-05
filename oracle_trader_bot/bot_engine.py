# bot_engine.py
import asyncio
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import logging
import signal
import sys
import pandas as pd
import os
from logging.handlers import RotatingFileHandler
import json 

from app.core.config import settings
from app.db.session import AsyncSessionFactory, init_db, async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

from app.exchange_clients.kucoin_futures_client import KucoinFuturesClient, KucoinAuthError, KucoinRequestError
from app.indicators.technical_indicators import calculate_indicators
from app.analysis.market_regime import determine_market_regime, MarketRegimeInfo
from app.strategies.trend_following_strategy import generate_trend_signal
from app.strategies.range_trading_strategy import generate_range_signal
from app.schemas.trading_signal import TradingSignal, TradeDirection
from app.schemas.trade import TradeCreate as TradeCreateSchema, TradeUpdate as TradeUpdateSchema
from app.models.trade import Trade as TradeModel, TradeStatus
from app.models.bot_settings import BotSettings as BotSettingsModel, TradeAmountMode
from app.crud import crud_trade, crud_bot_settings

# New service layer imports
from app.services.trade_manager import TradeManager
from app.services.signal_generator import SignalGenerator
from app.services.order_dispatcher import OrderDispatcher
from app.services.strategy_engine import StrategyEngine
from app.analysis.multi_timeframe import MultiTimeframeAnalyzer
from app.analysis.market_condition_detector import MarketConditionDetector

import aiohttp

# --- Configure logging to file and console ---
os.makedirs(settings.LOG_DIR, exist_ok=True)
bot_engine_log_path = os.path.join(settings.LOG_DIR, settings.BOT_ENGINE_LOG_FILE)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Keeping DEBUG for detailed troubleshooting

if logger.hasHandlers():
    logger.handlers.clear()

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] [BotEngine] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
logger.addHandler(console_handler)

file_handler = RotatingFileHandler(
    bot_engine_log_path,
    maxBytes=settings.MAX_LOG_FILE_SIZE_MB * 1024 * 1024,
    backupCount=settings.LOG_FILE_BACKUP_COUNT
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] [BotEngine] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
logger.addHandler(file_handler)
# --- End logging configuration ---

# --- WebSocket Communication Setup ---
ANALYSIS_LOG_API_URL = "http://127.0.0.1:8000/api/v1/analysis-logs/internal-publish" 

async def send_analysis_log(log_data: Dict[str, Any]):
    if global_aiohttp_session and not global_aiohttp_session.closed:
        try:
            response = await global_aiohttp_session.post(ANALYSIS_LOG_API_URL, json=log_data, timeout=5)
            response.raise_for_status() 
        except asyncio.TimeoutError:
            logger.warning(f"Bot Engine: Timeout sending analysis log to WebSocket endpoint.")
        except aiohttp.ClientError as e:
            logger.error(f"Bot Engine: Failed to send analysis log to WebSocket endpoint: {e}", exc_info=False)
        except Exception as e:
            logger.error(f"Bot Engine: Unexpected error sending analysis log: {e}", exc_info=True)
    else:
        logger.warning("Bot Engine: aiohttp session not available for sending analysis log.")

# --- End WebSocket Communication Setup ---


global_aiohttp_session: Optional[aiohttp.ClientSession] = None
kucoin_client: Optional[KucoinFuturesClient] = None
main_loop_task: Optional[asyncio.Task] = None
current_bot_db_settings: Optional[BotSettingsModel] = None

# Service layer instances
trade_manager: Optional[TradeManager] = None
signal_generator: Optional[SignalGenerator] = None
order_dispatcher: Optional[OrderDispatcher] = None
strategy_engine: Optional[StrategyEngine] = None
multi_timeframe_analyzer: Optional[MultiTimeframeAnalyzer] = None
market_condition_detector: Optional[MarketConditionDetector] = None

async def initialize_dependencies():
    """Initializes global dependencies like DB and Kucoin client."""
    global global_aiohttp_session, kucoin_client, current_bot_db_settings
    global trade_manager, signal_generator, order_dispatcher, strategy_engine
    global multi_timeframe_analyzer, market_condition_detector
    
    logger.info("Bot Engine: Initializing database...")
    await init_db()
    
    if global_aiohttp_session is None or global_aiohttp_session.closed:
        global_aiohttp_session = aiohttp.ClientSession()
        logger.info("Bot Engine: Global aiohttp.ClientSession created for Kucoin client.")

    try:
        if kucoin_client is None: 
            kucoin_client = KucoinFuturesClient(external_session=global_aiohttp_session)
        await kucoin_client._ensure_markets_loaded()
        logger.info("Bot Engine: KucoinFuturesClient initialized and markets loaded.")
        
        # Initialize service layer
        trade_manager = TradeManager(kucoin_client)
        signal_generator = SignalGenerator()
        order_dispatcher = OrderDispatcher(kucoin_client)
        strategy_engine = StrategyEngine()
        multi_timeframe_analyzer = MultiTimeframeAnalyzer(kucoin_client)
        market_condition_detector = MarketConditionDetector()
        
        logger.info("Bot Engine: Service layer initialized successfully.")
        
    except Exception as e:
        logger.error(f"Bot Engine: CRITICAL - Failed to initialize KucoinFuturesClient: {e}", exc_info=True)
        kucoin_client = None; return

    async with AsyncSessionFactory() as db:
        try:
            current_bot_db_settings = await crud_bot_settings.get_bot_settings(db)
            if current_bot_db_settings:
                logger.info(f"Bot Engine: Successfully loaded bot settings from DB: MaxTrades={current_bot_db_settings.max_concurrent_trades}, Mode='{current_bot_db_settings.trade_amount_mode}', FixedUSD={current_bot_db_settings.fixed_trade_amount_usd}, PercBalance={current_bot_db_settings.percentage_trade_amount}")
            else:
                logger.error("Bot Engine: CRITICAL - Failed to load or create bot settings from DB.")
        except Exception as e_settings:
            logger.error(f"Bot Engine: CRITICAL - Error fetching bot settings from DB: {e_settings}", exc_info=True)
            current_bot_db_settings = None

async def shutdown_dependencies():
    """Gracefully shuts down all dependencies."""
    global global_aiohttp_session, kucoin_client, main_loop_task
    logger.info("Bot Engine: Graceful shutdown sequence initiated...")

    if main_loop_task and not main_loop_task.done():
        logger.info("Bot Engine: Cancelling the main trading loop...")
        main_loop_task.cancel()
        try:
            # Await the task to ensure it has a chance to complete cancellation logic
            await main_loop_task
        except asyncio.CancelledError:
            logger.info("Bot Engine: Main trading loop successfully cancelled.")
        except Exception as e_loop_cancel:
            logger.error(f"Bot Engine: Error during main loop cancellation: {e_loop_cancel}", exc_info=True)
    
    if kucoin_client: 
        logger.info("Bot Engine: Closing Kucoin client session (custom close_session)...")
        try:
            await kucoin_client.close_session() 
            logger.info("Bot Engine: Kucoin client custom session closed.")
        except Exception as e_kc_close:
            logger.error(f"Bot Engine: Error closing Kucoin client custom session: {e_kc_close}", exc_info=True)
        
        if hasattr(kucoin_client.exchange, 'close') and callable(kucoin_client.exchange.close):
            logger.info("Bot Engine: Closing underlying ccxt exchange instance...")
            try:
                await kucoin_client.exchange.close() 
                logger.info("Bot Engine: Underlying ccxt exchange instance closed.")
            except Exception as e_ccxt_close:
                logger.error(f"Bot Engine: Error closing underlying ccxt exchange instance: {e_ccxt_close}", exc_info=True)
    
    if global_aiohttp_session and not global_aiohttp_session.closed:
        logger.info("Bot Engine: Closing global aiohttp.ClientSession...")
        try:
            await global_aiohttp_session.close()
            logger.info("Bot Engine: Global aiohttp.ClientSession closed.")
        except Exception as e_aio_close:
            logger.error(f"Bot Engine: Error closing global aiohttp session: {e_aio_close}", exc_info=True)
    
    if async_engine and hasattr(async_engine, 'dispose') and callable(async_engine.dispose): 
        logger.info("Bot Engine: Disposing database engine...")
        try: 
            await async_engine.dispose()
            logger.info("Bot Engine: Database engine disposed.")
        except Exception as e_db_dispose:
            logger.error(f"Bot Engine: Error disposing database engine: {e_db_dispose}", exc_info=True)
    
    logger.info("Bot Engine: Dependencies shut down complete.")

async def get_current_usdt_balance(client: KucoinFuturesClient) -> float:
    overview = await client.get_account_overview()
    if overview:
        if 'USDT' in overview and isinstance(overview['USDT'], dict) and overview['USDT'].get('free') is not None:
            return float(overview['USDT']['free'])
        elif overview.get('info', {}).get('data', {}).get('availableBalance') is not None:
            try:
                return float(overview['info']['data']['availableBalance'])
            except (TypeError, ValueError, KeyError) as e:
                logger.warning(f"Could not parse 'availableBalance' from KuCoin raw info: {e}")
        else:
            usdt_balance = overview.get('free', {}).get('USDT')
            if usdt_balance is not None:
                return float(usdt_balance)
    logger.warning("Could not determine available USDT balance for percentage-based trade amount. Returning 0.0")
    return 0.0


async def manage_existing_trade(
    db: AsyncSession, 
    trade_in_db: TradeModel, 
    symbol: str 
):
    if not kucoin_client: 
        logger.error(f"Bot Engine ({symbol}): Kucoin client not available in manage_existing_trade.")
        return
        
    logger.info(f"Bot Engine ({symbol}): Managing existing open DB trade ID: {trade_in_db.id}, Status in DB: {trade_in_db.status.value if trade_in_db.status else 'N/A'}")
    await send_analysis_log({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "INFO",
        "symbol": symbol,
        "strategy": "N/A",
        "message": f"Managing existing open trade ID: {trade_in_db.id}, Status in DB: {trade_in_db.status.value if trade_in_db.status else 'N/A'}",
        "decision": "MANAGEMENT"
    })

    open_positions_on_exchange = await kucoin_client.fetch_open_positions(symbol=trade_in_db.symbol) 
    
    logger.debug(f"Bot Engine ({symbol}): Raw open_positions_on_exchange response: {open_positions_on_exchange}") 
    
    position_is_live_on_exchange = False
    current_position_details = None 
    if open_positions_on_exchange: 
        # Iterate through positions as fetch_open_positions might return multiple or sometimes empty lists
        for pos in open_positions_on_exchange:
            current_qty = float(pos.get('info', {}).get('currentQty', '0')) # KuCoin specific field for current position quantity
            contracts_unified = pos.get('contracts', 0.0) # CCXT unified field for position size
            
            # Check for non-negligible quantity (avoid tiny dust positions)
            if abs(current_qty) > 1e-9 or abs(contracts_unified) > 1e-9: 
                position_is_live_on_exchange = True
                current_position_details = pos # Keep details of the live position
                break # Found a live position, no need to check others
    
    logger.debug(f"Bot Engine ({symbol}): position_is_live_on_exchange: {position_is_live_on_exchange}") 

    if position_is_live_on_exchange:
        logger.info(f"Bot Engine ({symbol}): Position for DB trade ID {trade_in_db.id} IS STILL CONSIDERED OPEN on exchange. Details: {current_position_details}")
        await send_analysis_log({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "INFO",
            "symbol": symbol,
            "strategy": "N/A",
            "message": f"Trade ID {trade_in_db.id} still open on exchange.",
            "decision": "HOLD"
        })
        return

    logger.info(f"Bot Engine ({symbol}): Position for DB trade ID {trade_in_db.id} appears CLOSED on exchange. Attempting to fetch closing trade details...")
    await send_analysis_log({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "INFO",
        "symbol": symbol,
        "strategy": "N/A",
        "message": f"Trade ID {trade_in_db.id} detected as closed on exchange. Fetching details.",
        "decision": "CLOSE_DETECTED"
    })
    
    since_timestamp_ms = int(trade_in_db.timestamp_opened.timestamp() * 1000) if trade_in_db.timestamp_opened else None
    
    my_trades_fills = await kucoin_client.fetch_my_recent_trades(symbol=trade_in_db.symbol, since=since_timestamp_ms, limit=20) 
    logger.debug(f"Bot Engine ({symbol}): Raw my_trades_fills response: {my_trades_fills}") 

    closing_fills: List[Dict[str, Any]] = [] 

    if not my_trades_fills:
        logger.warning(f"Bot Engine ({symbol}): Could not fetch recent fills for trade ID {trade_in_db.id}. Updating status to an estimated closed state.")
        closed_status = TradeStatus.CLOSED_EXCHANGE 
        exit_reason_str = "Position closed on exchange; specific fill details not found in recent history."
        trade_update_schema = TradeUpdateSchema(
            status=closed_status, 
            exit_reason=exit_reason_str,
            timestamp_closed=datetime.now(timezone.utc)
        )
        try:
            await crud_trade.update_trade(db=db, db_trade=trade_in_db, trade_in=trade_update_schema)
            await db.commit()
            logger.info(f"Bot Engine ({symbol}): Trade ID {trade_in_db.id} status updated to {closed_status.value} (no fill details).")
            await send_analysis_log({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "WARNING",
                "symbol": symbol,
                "strategy": "N/A",
                "message": f"Trade ID {trade_in_db.id} closed on exchange, details missing. Updated DB.",
                "decision": "CLOSED_NO_FILLS"
            })
        except Exception as e_db_update:
            logger.error(f"Bot Engine ({symbol}): DB update failed for trade ID {trade_in_db.id} (no fill details): {e_db_update}", exc_info=True)
            await db.rollback()
        return

    remaining_qty_to_close = float(trade_in_db.quantity) if trade_in_db.quantity is not None else 0.0
    db_trade_direction_str = trade_in_db.direction.value.lower() 
    logger.debug(f"Bot Engine ({symbol}): Starting fill processing. Remaining Qty: {remaining_qty_to_close}, Direction: {db_trade_direction_str}") 

    for ex_trade in sorted(my_trades_fills, key=lambda x: x.get('timestamp', 0)): 
        if since_timestamp_ms and ex_trade.get('timestamp') is not None and ex_trade['timestamp'] < since_timestamp_ms:
            continue

        fill_side = ex_trade.get('side', '').lower()
        fill_amount = float(ex_trade.get('amount', 0.0))
        is_closing_fill = False
        if db_trade_direction_str == 'long' and fill_side == 'sell':
            is_closing_fill = True
        elif db_trade_direction_str == 'short' and fill_side == 'buy':
            is_closing_fill = True
        
        # Only consider fills that contribute to closing the position
        if is_closing_fill and remaining_qty_to_close > 1e-9: 
            amount_from_this_fill = min(remaining_qty_to_close, fill_amount)
            closing_fills.append({ 
                'price': float(ex_trade.get('price', 0.0)),
                'amount': amount_from_this_fill,
                'cost': float(ex_trade.get('cost', 0.0)), 
                'fee_cost': float(ex_trade.get('fee', {}).get('cost', 0.0)),
                'fee_currency': ex_trade.get('fee', {}).get('currency'),
                'timestamp': ex_trade.get('timestamp'),
                'order_id': ex_trade.get('order')
            })
            remaining_qty_to_close -= amount_from_this_fill
            logger.debug(f"Bot Engine ({symbol}): Found closing fill. Amount: {amount_from_this_fill}, Remaining Qty: {remaining_qty_to_close}") 
            if remaining_qty_to_close <= 1e-9: # Position fully closed by fills
                break 
            
    logger.debug(f"Bot Engine ({symbol}): Final closing_fills collected: {closing_fills}") 

    if not closing_fills:
        logger.warning(f"Bot Engine ({symbol}): No specific closing fills found matching quantity/side for trade ID {trade_in_db.id}. Updating status to an estimated closed state.")
        if not position_is_live_on_exchange: 
            update_data_ambiguous = TradeUpdateSchema(status=TradeStatus.CLOSED_EXCHANGE, exit_reason="Position closed on exchange; specific fill details not found in recent history.")
            await crud_trade.update_trade(db=db, db_trade=trade_in_db, trade_in=update_data_ambiguous)
            await db.commit()
        return

    total_exit_value = sum(cf['price'] * cf['amount'] for cf in closing_fills)
    total_closed_quantity = sum(cf['amount'] for cf in closing_fills)
    avg_exit_price = total_exit_value / total_closed_quantity if total_closed_quantity > 0 else None
    total_exit_fees = sum(cf['fee_cost'] for cf in closing_fills)
    last_exit_timestamp_ms = closing_fills[-1].get('timestamp') 
    timestamp_closed_dt = datetime.fromtimestamp(last_exit_timestamp_ms / 1000, tz=timezone.utc) if last_exit_timestamp_ms else datetime.now(timezone.utc)
    exit_order_id_str = closing_fills[-1].get('order_id') 

    pnl = None; pnl_percentage = None
    entry_price_db = float(trade_in_db.entry_price) if trade_in_db.entry_price is not None else None
    quantity_db = float(trade_in_db.quantity) if trade_in_db.quantity is not None else None
    
    if entry_price_db and avg_exit_price and quantity_db and total_closed_quantity >= quantity_db - 1e-9 : 
        if trade_in_db.direction == TradeDirection.LONG: pnl = (avg_exit_price - entry_price_db) * quantity_db 
        elif trade_in_db.direction == TradeDirection.SHORT: pnl = (entry_price_db - avg_exit_price) * quantity_db
        if pnl is not None:
            pnl -= total_exit_fees 
            if trade_in_db.entry_fee: pnl -= float(trade_in_db.entry_fee) 
        if trade_in_db.margin_used_initial and float(trade_in_db.margin_used_initial) != 0 and pnl is not None:
            pnl_percentage = (pnl / float(trade_in_db.margin_used_initial)) * 100
    
    # Determine final_status and exit_reason based on fills and initial SL/TP
    exit_reason_str = "Closed_by_Exchange_Fills"; final_status = TradeStatus.CLOSED_EXCHANGE 
    
    # Check if a manual close via API triggered this (only if API reports manual close)
    # This requires API to set exit_reason to 'Manual_Close_Action' or similar
    if trade_in_db.exit_reason == "Manual_Close_Action": # This checks the DB's existing exit_reason
        exit_reason_str = "Closed_by_Manual_Action"
        final_status = TradeStatus.CLOSED_MANUAL
    elif trade_in_db.stop_loss_initial and avg_exit_price: # Infer SL hit
        if (trade_in_db.direction == TradeDirection.LONG and avg_exit_price <= trade_in_db.stop_loss_initial) or \
           (trade_in_db.direction == TradeDirection.SHORT and avg_exit_price >= trade_in_db.stop_loss_initial):
            exit_reason_str = "StopLoss_Hit_Inferred"; final_status = TradeStatus.CLOSED_SL
    elif trade_in_db.take_profit_initial and avg_exit_price: # Infer TP hit
        if (trade_in_db.direction == TradeDirection.LONG and avg_exit_price >= trade_in_db.take_profit_initial) or \
           (trade_in_db.direction == TradeDirection.SHORT and avg_exit_price <= trade_in_db.take_profit_initial):
            exit_reason_str = "TakeProfit_Hit_Inferred"; final_status = TradeStatus.CLOSED_TP

    logger.info(f"Bot Engine ({symbol}): Updating trade ID {trade_in_db.id} as {final_status.value}. Avg Exit: {avg_exit_price}, Qty: {total_closed_quantity}, PNL: {pnl}, Fees: {total_exit_fees}, Reason: {exit_reason_str}")
    trade_update_schema = TradeUpdateSchema(status=final_status, exit_price=avg_exit_price, timestamp_closed=timestamp_closed_dt, exit_order_id=exit_order_id_str, pnl=pnl, pnl_percentage=pnl_percentage, exit_fee=total_exit_fees, exit_reason=exit_reason_str)
    try:
        await crud_trade.update_trade(db=db, db_trade=trade_in_db, trade_in=trade_update_schema)
        await db.commit()
        logger.info(f"Bot Engine ({symbol}): Trade ID {trade_in_db.id} successfully updated in DB with closure details.")
        await send_analysis_log({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "INFO",
            "symbol": symbol,
            "strategy": "N/A",
            "message": f"Trade ID {trade_in_db.id} closed. PNL: {pnl:.2f}, Reason: {exit_reason_str}",
            "decision": "CLOSED"
        })
    except Exception as e_db_update:
        logger.error(f"Bot Engine ({symbol}): DB update failed for trade ID {trade_in_db.id} (no fill details): {e_db_update}", exc_info=True)
        await db.rollback()


async def process_symbol(
    symbol: str, 
    db_session_factory: sessionmaker,
    bot_config: BotSettingsModel 
):
    """Refactored process_symbol function using service layer."""
    if not kucoin_client:
        logger.error(f"Bot Engine ({symbol}): Kucoin client not initialized. Skipping.")
        return
    if not bot_config: 
        logger.error(f"Bot Engine ({symbol}): Bot configuration not available. Skipping.")
        return

    logger.info(f"Bot Engine ({symbol}): Starting processing cycle. Bot Config: MaxTrades={bot_config.max_concurrent_trades}, Mode='{bot_config.trade_amount_mode}', FixedUSD={bot_config.fixed_trade_amount_usd}, PercBalance={bot_config.percentage_trade_amount}")
    await send_analysis_log({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "INFO",
        "symbol": symbol,
        "strategy": "N/A",
        "message": f"Starting analysis cycle for {symbol}.",
        "decision": "ANALYZE_START"
    })

    try:
        async with db_session_factory() as db: 
            # Check for existing trades using TradeManager
            active_trade_for_symbol: Optional[TradeModel] = await crud_trade.get_open_trade_by_symbol(db, symbol=symbol)

            if active_trade_for_symbol:
                logger.info(f"Bot Engine ({symbol}): Found active trade in DB (ID: {active_trade_for_symbol.id}). Managing existing trade...")
                # Use TradeManager service for existing trade management
                result = await trade_manager.manage_existing_trade(db, active_trade_for_symbol, symbol)
                await send_analysis_log({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": "INFO",
                    "symbol": symbol,
                    "strategy": "TradeManager",
                    "message": f"Trade management result: {result['action']}",
                    "decision": result['action']
                })
                return 

            # Check concurrent trade limits
            open_trades_count_from_db = await crud_trade.count_open_trades(db) 
            logger.info(f"Bot Engine: Currently {open_trades_count_from_db} open trades in DB. Max allowed by config: {bot_config.max_concurrent_trades}")
            if open_trades_count_from_db >= bot_config.max_concurrent_trades:
                logger.info(f"Bot Engine ({symbol}): Max concurrent trades ({bot_config.max_concurrent_trades}) reached. Skipping new signal generation for {symbol}.")
                await send_analysis_log({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": "WARNING",
                    "symbol": symbol,
                    "strategy": "N/A",
                    "message": f"Skipping new signal for {symbol}: Max concurrent trades reached ({open_trades_count_from_db}/{bot_config.max_concurrent_trades}).",
                    "decision": "SKIPPED_MAX_TRADES"
                })
                return
            
            # Use StrategyEngine for signal generation
            logger.debug(f"Bot Engine ({symbol}): No active trade in DB. Using StrategyEngine for signal generation.")
            ohlcv_list = await kucoin_client.fetch_ohlcv(symbol, settings.PRIMARY_TIMEFRAME_BOT, limit=settings.CANDLE_LIMIT_BOT)
            
            # Get current open positions for signal generator (simplified - we already checked this symbol)
            current_open_positions = []
            
            # Generate signal using StrategyEngine
            trading_signal = await strategy_engine.analyze_and_generate_signal(
                symbol=symbol,
                ohlcv_data=ohlcv_list,
                current_open_positions=current_open_positions,
                bot_config=bot_config
            )

            if not trading_signal:
                logger.info(f"Bot Engine ({symbol}): No signal generated by StrategyEngine.")
                await send_analysis_log({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": "INFO",
                    "symbol": symbol,
                    "strategy": "StrategyEngine",
                    "message": f"No signal generated for {symbol}.",
                    "decision": "NO_SIGNAL"
                })
                return

            logger.info(f"Bot Engine ({symbol}): Signal generated: {trading_signal.direction.value} by {trading_signal.strategy_name}, Strength: {trading_signal.signal_strength}, Leverage: {trading_signal.suggested_leverage}x")
            await send_analysis_log({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "INFO",
                "symbol": symbol,
                "strategy": trading_signal.strategy_name,
                "message": f"Signal generated: {trading_signal.direction.value}, Strength: {trading_signal.signal_strength:.2f}",
                "decision": "SIGNAL_GENERATED",
                "details": {
                    "direction": trading_signal.direction.value,
                    "entry_price": trading_signal.entry_price,
                    "stop_loss": trading_signal.stop_loss,
                    "take_profit": trading_signal.take_profit,
                    "leverage": trading_signal.suggested_leverage
                }
            })
            
            # Use OrderDispatcher for order execution
            # Calculate trade amount
            margin_to_use = await order_dispatcher.calculate_trade_amount(bot_config, symbol)
            
            # Calculate order amount
            order_amount = await order_dispatcher.calculate_order_amount(trading_signal, margin_to_use, symbol)
            
            if not order_amount:
                logger.warning(f"Bot Engine ({symbol}): Failed to calculate valid order amount.")
                await send_analysis_log({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": "WARNING",
                    "symbol": symbol,
                    "strategy": trading_signal.strategy_name,
                    "message": f"Failed to calculate valid order amount for {symbol}.",
                    "decision": "ORDER_CALCULATION_FAILED"
                })
                return
            
            # Validate order parameters
            if not await order_dispatcher.validate_order_parameters(trading_signal, symbol):
                logger.warning(f"Bot Engine ({symbol}): Order parameter validation failed.")
                await send_analysis_log({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": "WARNING",
                    "symbol": symbol,
                    "strategy": trading_signal.strategy_name,
                    "message": f"Order parameter validation failed for {symbol}.",
                    "decision": "ORDER_VALIDATION_FAILED"
                })
                return
            
            # Execute order
            logger.info(f"Bot Engine ({symbol}): Executing order. Amount: {order_amount:.8f}, Margin: {margin_to_use:.2f} USD")
            await send_analysis_log({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "INFO",
                "symbol": symbol,
                "strategy": trading_signal.strategy_name,
                "message": f"Executing order for {symbol}: Side={trading_signal.direction.value}, Amount={order_amount:.8f}",
                "decision": "ORDER_EXECUTING"
            })

            order_info = await order_dispatcher.execute_order(trading_signal, order_amount, symbol)

            if order_info and order_info.get('id'):
                logger.info(f"Bot Engine ({symbol}): Order executed successfully. Order ID: {order_info.get('id')}")
                await send_analysis_log({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": "SUCCESS",
                    "symbol": symbol,
                    "strategy": trading_signal.strategy_name,
                    "message": f"Order executed successfully for {symbol}. Order ID: {order_info.get('id')}",
                    "decision": "ORDER_EXECUTED",
                    "details": order_info
                })
                
                # Use TradeManager to create trade record
                market_regime_label = strategy_engine.market_condition_cache.get(symbol, {}).get('regime', {}).get('descriptive_label', 'Unknown')
                
                db_trade = await trade_manager.create_trade_record(
                    db=db,
                    order_info=order_info,
                    trading_signal=trading_signal,
                    margin_used=margin_to_use,
                    market_regime_label=market_regime_label
                )
                
                if db_trade:
                    logger.info(f"Bot Engine ({symbol}): Trade record created successfully. DB ID: {db_trade.id}")
                    await send_analysis_log({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "level": "INFO",
                        "symbol": symbol,
                        "strategy": trading_signal.strategy_name,
                        "message": f"Trade record created. DB ID: {db_trade.id}",
                        "decision": "TRADE_RECORDED"
                    })
                else:
                    logger.error(f"Bot Engine ({symbol}): Failed to create trade record.")
                    await send_analysis_log({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "level": "ERROR",
                        "symbol": symbol,
                        "strategy": trading_signal.strategy_name,
                        "message": f"Failed to create trade record for {symbol}.",
                        "decision": "TRADE_RECORD_FAILED"
                    })
            else:
                logger.error(f"Bot Engine ({symbol}): Order execution failed.")
                await send_analysis_log({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": "ERROR",
                    "symbol": symbol,
                    "strategy": trading_signal.strategy_name,
                    "message": f"Order execution failed for {symbol}.",
                    "decision": "ORDER_FAILED"
                })

    except KucoinAuthError as e: 
        logger.error(f"Bot Engine ({symbol}): Auth error: {e}", exc_info=False) 
        await send_analysis_log({
            "timestamp": datetime.now(timezone.utc).isoformat(), 
            "level": "ERROR", 
            "symbol": symbol, 
            "strategy": "N/A", 
            "message": f"Auth error: {e}", 
            "decision": "AUTH_ERROR"
        })
    except KucoinRequestError as e: 
        logger.error(f"Bot Engine ({symbol}): Exchange request error: {e}", exc_info=False)
        await send_analysis_log({
            "timestamp": datetime.now(timezone.utc).isoformat(), 
            "level": "ERROR", 
            "symbol": symbol, 
            "strategy": "N/A", 
            "message": f"Exchange request error: {e}", 
            "decision": "EXCHANGE_ERROR"
        })
    except Exception as e: 
        logger.error(f"Bot Engine ({symbol}): Unexpected error: {e}", exc_info=True)
        await send_analysis_log({
            "timestamp": datetime.now(timezone.utc).isoformat(), 
            "level": "CRITICAL", 
            "symbol": symbol, 
            "strategy": "N/A", 
            "message": f"Unexpected error in processing {symbol}: {e}", 
            "decision": "UNEXPECTED_ERROR"
        })




async def main_bot_loop_internal():
    """The main asynchronous loop for the trading bot."""
    global main_loop_task, current_bot_db_settings
    
    # Dependencies are initialized once before the loop starts
    # This function is now called directly in the 'run_bot' wrapper, not here.
    
    if not kucoin_client or not current_bot_db_settings or not strategy_engine: 
        logger.critical("Bot client, Bot DB Settings, or Service Layer could not be initialized. Bot cannot start.")
        # No need to close sessions here, run_bot will handle shutdown_dependencies if this returns.
        await send_analysis_log({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "CRITICAL",
            "symbol": "N/A",
            "strategy": "N/A",
            "message": "Bot dependencies (Kucoin client, DB settings, or service layer) failed to initialize. Bot cannot start.",
            "decision": "BOT_START_FAILED"
        })
        return

    try:
        while True: 
            # Check for current_bot_db_settings periodically in case they are updated
            # or could be reloaded if needed. For now, assume it's stable after init.
            # If dynamic settings updates are needed, this would be the place to reload them.
            
            logger.info(f"Bot Engine: Starting new trading cycle at {datetime.now(timezone.utc).isoformat()}")
            await send_analysis_log({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "INFO",
                "symbol": "N/A",
                "strategy": "N/A",
                "message": "Starting new trading cycle.",
                "decision": "CYCLE_START"
            })
            
            symbols_to_process = current_bot_db_settings.symbols_to_trade
            if not symbols_to_process:
                logger.warning("Bot Engine: No symbols configured to trade. Sleeping and re-checking settings.")
                await send_analysis_log({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": "WARNING",
                    "symbol": "N/A",
                    "strategy": "N/A",
                    "message": "No symbols configured to trade. Bot is idle.",
                    "decision": "NO_SYMBOLS_CONFIGURED"
                })
                await asyncio.sleep(settings.LOOP_SLEEP_DURATION_SECONDS_BOT)
                # Attempt to reload settings if no symbols to trade
                async with AsyncSessionFactory() as db:
                    current_bot_db_settings = await crud_bot_settings.get_bot_settings(db)
                continue # Skip to next loop iteration
            
            logger.info(f"Bot Engine: Symbols to process from DB: {symbols_to_process}")
            
            for symbol_to_trade in symbols_to_process: 
                try:
                    await process_symbol(symbol_to_trade, AsyncSessionFactory, current_bot_db_settings) 
                except asyncio.CancelledError:
                    raise # Re-raise CancelledError to stop the loop gracefully
                except Exception as e_task_run: 
                    logger.error(f"Bot Engine: Error processing symbol {symbol_to_trade}: {e_task_run}", exc_info=True)
                
                if len(symbols_to_process) > 1: 
                    logger.debug(f"Bot Engine: Delaying {settings.DELAY_BETWEEN_SYMBOL_PROCESSING_SECONDS_BOT}s between symbols.")
                    await asyncio.sleep(settings.DELAY_BETWEEN_SYMBOL_PROCESSING_SECONDS_BOT) 

            logger.info(f"Bot Engine: Trading cycle complete. Waiting {settings.LOOP_SLEEP_DURATION_SECONDS_BOT}s for next cycle...")
            
            # Log service layer performance metrics every 10 cycles (adjust as needed)
            if hasattr(main_bot_loop_internal, 'cycle_count'):
                main_bot_loop_internal.cycle_count += 1
            else:
                main_bot_loop_internal.cycle_count = 1
            
            if main_bot_loop_internal.cycle_count % 10 == 0:
                # Log strategy performance
                strategy_performance = strategy_engine.get_strategy_performance()
                market_conditions = strategy_engine.get_market_conditions_summary()
                
                logger.info(f"Bot Engine: Service Layer Metrics (Cycle {main_bot_loop_internal.cycle_count}):")
                logger.info(f"  - Strategy Performance: {len(strategy_performance)} strategies tracked")
                logger.info(f"  - Market Conditions: {market_conditions.get('total_symbols', 0)} symbols analyzed")
                logger.info(f"  - Trending Markets: {market_conditions.get('trending_count', 0)}")
                logger.info(f"  - Ranging Markets: {market_conditions.get('ranging_count', 0)}")
                
                await send_analysis_log({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": "INFO",
                    "symbol": "N/A",
                    "strategy": "ServiceLayer",
                    "message": f"Service layer metrics at cycle {main_bot_loop_internal.cycle_count}",
                    "decision": "METRICS_REPORT",
                    "details": {
                        "cycle_count": main_bot_loop_internal.cycle_count,
                        "strategy_performance": strategy_performance,
                        "market_conditions": market_conditions
                    }
                })
            
            await send_analysis_log({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "INFO",
                "symbol": "N/A",
                "strategy": "N/A",
                "message": "Trading cycle complete. Waiting for next cycle.",
                "decision": "CYCLE_END"
            })
            await asyncio.sleep(settings.LOOP_SLEEP_DURATION_SECONDS_BOT)
    except asyncio.CancelledError: 
        logger.info("Bot Engine: Main trading loop received CancelledError. Shutting down.")
        await send_analysis_log({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "INFO",
            "symbol": "N/A",
            "strategy": "N/A",
            "message": "Main trading loop cancelled by signal.",
            "decision": "BOT_STOPPED"
        })
    except Exception as e_loop: 
        logger.error(f"Bot Engine: Unhandled critical exception in main loop: {e_loop}", exc_info=True)
        await send_analysis_log({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "CRITICAL",
            "symbol": "N/A",
            "strategy": "N/A",
            "message": f"Unhandled critical exception in main loop: {e_loop}",
            "decision": "CRITICAL_ERROR"
        })

async def run_bot():
    """Wrapper function to run the bot engine, handle initialization and graceful shutdown."""
    global main_loop_task
    try:
        await initialize_dependencies()
        if kucoin_client and current_bot_db_settings:
            main_loop_task = asyncio.create_task(main_bot_loop_internal())
            await main_loop_task
        else:
            logger.critical("Bot dependencies could not be initialized. Exiting without running main loop.")
    except asyncio.CancelledError:
        logger.info("Bot Engine: run_bot task cancelled.")
    except Exception as e:
        logger.critical(f"Bot Engine: Critical error in run_bot wrapper: {e}", exc_info=True)
    finally:
        logger.info("Bot Engine: Initiating final dependency shutdown.")
        await shutdown_dependencies()
        logger.info("Bot Engine: All dependencies shut down.")
        # This is where the process should ideally exit cleanly if run_bot completes or is cancelled

# This is the new, robust signal handling and main execution block
if __name__ == "__main__":
    print("Starting Oracle Trader Bot Engine (Standalone)...")
    from dotenv import load_dotenv
    load_dotenv()

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Flag to track if graceful shutdown is initiated by signal
    _graceful_shutdown_initiated = False

    async def signal_handler_async():
        global _graceful_shutdown_initiated # CORRECTED: Use global to modify the flag
        if _graceful_shutdown_initiated:
            logger.info("Bot Engine: Graceful shutdown already initiated. Ignoring redundant signal.")
            return

        _graceful_shutdown_initiated = True
        logger.info("Bot Engine: Received OS signal (SIGINT/SIGTERM). Starting graceful shutdown...")
        
        # Get all running tasks excluding the current one (signal handler task) and tasks that are already done.
        pending_tasks = [task for task in asyncio.all_tasks(loop=loop) if task is not asyncio.current_task() and not task.done()]
        
        # Cancel all pending tasks
        for task in pending_tasks:
            task.cancel()
        
        # Wait for all tasks to complete their cancellation or finish
        try:
            # Giving more time for cancellation, and allowing it to complete before moving on
            await asyncio.wait_for(asyncio.gather(*pending_tasks, return_exceptions=True), timeout=30) 
        except asyncio.TimeoutError:
            logger.warning("Bot Engine: Some tasks did not finish cancelling within timeout during signal handling. Forcing shutdown.")
        except Exception as e_gather:
            logger.error(f"Bot Engine: Error during gathering tasks in signal handler: {e_gather}", exc_info=True)
            
        await shutdown_dependencies() # Perform cleanup of clients, DB etc.

        # Schedule the loop to stop and then exit.
        # This is safer than directly calling sys.exit() immediately,
        # giving the loop a chance to complete any pending low-level operations.
        # This ensures the process exits cleanly after cleanup.
        def _final_cleanup_and_exit():
            logger.info("Bot Engine: Executing final cleanup and exit sequence.")
            if loop.is_running():
                try:
                    # Attempt to stop the loop, if it's still running.
                    # This might be redundant if loop.run_until_complete(run_bot()) finishes naturally,
                    # but crucial if run_forever() or similar is used or if the loop is stuck.
                    loop.stop() 
                    logger.info("Bot Engine: Event loop stopped.")
                except RuntimeError as e:
                    logger.warning(f"Bot Engine: Could not stop loop: {e} (might already be stopping/stopped)")
            if not loop.is_closed():
                try:
                    loop.close()
                    logger.info("Bot Engine: Event loop closed.")
                except RuntimeError as e:
                    logger.warning(f"Bot Engine: Could not close loop: {e} (might already be closing/closed)")
            logger.info("Bot Engine: Process exiting.")
            sys.exit(0) # Exit the process cleanly

        # Schedule this final cleanup to run as soon as possible on the event loop
        loop.call_soon(_final_cleanup_and_exit) 

    for sig_name in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig_name, lambda: loop.create_task(signal_handler_async()))
            logger.info(f"Bot Engine: Registered signal handler for {sig_name.name}.")
        except (NotImplementedError, RuntimeError):
            logger.warning(f"Bot Engine: Could not register signal handler for {sig_name.name} (not implemented/runtime error).")

    try:
        # Run the main bot execution wrapper. This will block until run_bot completes (or is cancelled).
        loop.run_until_complete(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot Engine: KeyboardInterrupt caught outside of signal handler. Graceful shutdown should have been initiated by signal handler.")
        # If KeyboardInterrupt happens here, it means the signal handler might not have caught it (e.g., on Windows)
        # or it was a direct Ctrl+C.
        # We ensure _graceful_shutdown_initiated is set and call cleanup.
        if not _graceful_shutdown_initiated:
            logger.warning("Bot Engine: Manual KeyboardInterrupt. Initiating fallback shutdown.")
            asyncio.run(shutdown_dependencies()) # Run fallback cleanup synchronously
            # After fallback, also try to exit cleanly if loop is still running
            if loop.is_running():
                try:
                    loop.stop()
                except RuntimeError as e:
                    logger.warning(f"Bot Engine: Could not stop loop after fallback KeyboardInterrupt: {e}")
            if not loop.is_closed():
                try:
                    loop.close()
                except RuntimeError as e:
                    logger.warning(f"Bot Engine: Could not close loop after fallback KeyboardInterrupt: {e}")
            sys.exit(0) # Exit after fallback
    except Exception as e_main_run:
        logger.critical(f"Bot Engine: Unhandled exception in main execution block: {e_main_run}", exc_info=True)
    finally:
        logger.info("Bot Engine (main): Main execution block finished or exception occurred. Final checks for loop closure.")
        # This final block is a safety net. If sys.exit(0) was called from signal_handler_async,
        # this part might not be reached or the loop might already be closed.
        if loop.is_running():
            logger.warning("Bot Engine (main): Loop still running in final finally. Forcing stop.")
            loop.stop()
        if not loop.is_closed():
            logger.warning("Bot Engine (main): Loop not closed in final finally. Forcing close.")
            loop.close()
        print("Bot Engine fully shut down.")
