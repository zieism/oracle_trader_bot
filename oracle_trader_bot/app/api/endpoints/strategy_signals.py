# app/api/endpoints/strategy_signals.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional, List, Dict, Any
import logging
import pandas as pd

from app.api.dependencies import get_kucoin_client
from app.exchange_clients.kucoin_futures_client import KucoinFuturesClient
from app.indicators.technical_indicators import calculate_indicators
from app.analysis.market_regime import determine_market_regime 
from app.schemas.market_regime_schemas import MarketRegimeInfo # Import schema for type hint
from app.schemas.trading_signal import TradingSignal 

# Import strategy functions
from app.strategies.trend_following_strategy import generate_trend_signal
from app.strategies.range_trading_strategy import generate_range_signal

router = APIRouter()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO) # Set to DEBUG for more verbosity if needed

@router.get(
    "/generate-signal/{symbol}", 
    response_model=Optional[TradingSignal], 
    summary="Generate Trading Signal Based on Market Regime",
    description="Fetches OHLCV, calculates indicators, determines market regime, "
                "selects the appropriate strategy (Trend-Following or Range-Trading), "
                "and attempts to generate a trading signal."
)
async def get_strategy_signal( # Renamed endpoint function for clarity
    symbol: str, 
    timeframe: str = Query("1h", description="Timeframe e.g., '1m', '1h', '4h', '1d'"),
    limit: int = Query(200, description="Number of candles to fetch for analysis (e.g., 100-200)"),
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client)
):
    logger.info(f"SignalRequest: Received for {symbol}, TF:{timeframe}, Limit:{limit}")

    # 1. Fetch OHLCV data
    ohlcv_list = await kucoin_client.fetch_ohlcv(symbol, timeframe, limit=limit)
    if ohlcv_list is None or len(ohlcv_list) < 50: # Ensure enough data for indicators
        logger.warning(f"SignalRequest: Insufficient OHLCV data for {symbol} (got {len(ohlcv_list) if ohlcv_list else 0}).")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Insufficient OHLCV data for {symbol} on timeframe {timeframe} to generate a signal."
        )
    
    # 2. Calculate indicators
    df_with_indicators = calculate_indicators(ohlcv_list)
    if df_with_indicators is None or df_with_indicators.empty:
        logger.error(f"SignalRequest: Failed to calculate indicators for {symbol}.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indicator calculation failed for {symbol}."
        )

    # 3. Determine market regime
    market_regime_info: MarketRegimeInfo = determine_market_regime(df_with_indicators)
    logger.info(f"SignalRequest: Determined market regime for {symbol}: {market_regime_info.descriptive_label}")

    # 4. Select and execute strategy based on market regime
    # For this test, current_open_positions is empty. In a live bot, this would be fetched.
    current_open_positions: List[str] = [] 
    trading_signal_obj: Optional[TradingSignal] = None

    # --- Strategy Selection Logic ---
    # This can be made more sophisticated later (e.g., based on volatility + trend strength)
    if market_regime_info.is_trending:
        logger.info(f"SignalRequest: Attempting Trend-Following strategy for {symbol} (Regime: {market_regime_info.descriptive_label})")
        trading_signal_obj = generate_trend_signal(
            symbol=symbol,
            df_with_indicators=df_with_indicators,
            market_regime_info=market_regime_info,
            current_open_positions_symbols=current_open_positions
        )
    elif market_regime_info.trend_direction == "SIDEWAYS": # Or check specific RANGING label
        logger.info(f"SignalRequest: Attempting Range-Trading strategy for {symbol} (Regime: {market_regime_info.descriptive_label})")
        trading_signal_obj = generate_range_signal(
            symbol=symbol,
            df_with_indicators=df_with_indicators,
            market_regime_info=market_regime_info,
            current_open_positions_symbols=current_open_positions
        )
    else:
        logger.info(f"SignalRequest: No suitable strategy for current market regime '{market_regime_info.descriptive_label}' for {symbol}.")


    if trading_signal_obj:
        logger.info(f"SignalRequest: Signal generated for {symbol} by {trading_signal_obj.strategy_name}: {trading_signal_obj.direction.value}")
        return trading_signal_obj
    else:
        logger.info(f"SignalRequest: No signal generated for {symbol} under regime '{market_regime_info.descriptive_label}'.")
        return None # FastAPI will return 200 OK with null body if response_model is Optional