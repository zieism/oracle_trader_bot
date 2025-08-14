# backend/app/api/routers/analysis.py
"""
Analysis Router - Market Data & Technical Analysis

Provides market data retrieval, technical indicator calculations, and market regime analysis.
Combines OHLCV data fetching with advanced technical analysis capabilities.

Routes:
- GET /api/v1/market/ohlcv/{symbol} - Get OHLCV price data for symbol
- GET /api/v1/market/ohlcv-with-indicators/{symbol} - Get OHLCV data with technical indicators and market regime
- WebSocket /api/ws/analysis-logs - Real-time analysis logs stream
- POST /api/internal/analysis-logs/internal-publish - Internal endpoint for log publishing
"""

import asyncio
import json
import logging
from typing import List, Any, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket, WebSocketDisconnect, Request
from pydantic import BaseModel
import pandas as pd
import numpy as np

from app.api.dependencies import get_kucoin_client
from app.exchange_clients.kucoin_futures_client import KucoinFuturesClient
from app.indicators.technical_indicators import calculate_indicators
from app.analysis.market_regime import determine_market_regime
from app.schemas.market_regime_schemas import MarketRegimeInfo, OHLCVWithIndicatorsAndRegimeResponse

router = APIRouter()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Global list to keep track of active WebSocket connections
# In production, consider using Redis Pub/Sub for scalability across multiple worker processes
active_connections: List[WebSocket] = []

# Pydantic model for incoming analysis log entries from bot_engine
class AnalysisLogEntry(BaseModel):
    timestamp: str
    level: str
    symbol: str
    strategy: str
    message: str
    decision: str
    details: Optional[Dict[str, Any]] = None

# ============================================================================
# MARKET DATA ENDPOINTS
# ============================================================================

@router.get(
    "/ohlcv/{symbol}", # Full path: /api/v1/market/ohlcv/{symbol}
    response_model=List[List[Any]],
    summary="Get OHLCV Price Data",
    tags=["Market Data"]
)
async def get_ohlcv_data(
    symbol: str,
    timeframe: str = Query("1h", description="Timeframe string (e.g., '1m', '5m', '1h', '1d', '1w', '1M')"),
    since: Optional[int] = Query(None, description="Fetch OHLCV since this timestamp (milliseconds UTC)"),
    limit: Optional[int] = Query(None, description="Number of OHLCV candles to fetch (exchange default if None, max varies)"),
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client)
):
    """
    Fetch OHLCV (Open, High, Low, Close, Volume) price data for a given symbol.
    
    - **symbol**: Trading pair symbol (e.g., 'BTC/USDT:USDT')
    - **timeframe**: Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d, etc.)
    - **since**: Start timestamp in milliseconds UTC (optional)
    - **limit**: Maximum number of candles to fetch (optional)
    
    Returns raw OHLCV data as list of [timestamp, open, high, low, close, volume].
    """
    if not symbol:
        logger.warning("Symbol parameter missing for /ohlcv endpoint")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Symbol parameter is required.")
    
    logger.info(f"Fetching OHLCV for {symbol}, timeframe {timeframe}, limit {limit}, since {since}")
    try:
        ohlcv_data = await kucoin_client.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            since=since,
            limit=limit
        )
        if ohlcv_data is None:
            logger.warning(f"Could not fetch OHLCV data for '{symbol}' from KuCoin (client returned None).")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Could not fetch OHLCV data for '{symbol}' from KuCoin, or the symbol/timeframe is invalid as per exchange."
            )
        logger.info(f"Successfully fetched {len(ohlcv_data)} OHLCV candles for {symbol}")
        return ohlcv_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /ohlcv/{symbol} endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching OHLCV data for '{symbol}': {str(e)}"
        )

@router.get(
    "/ohlcv-with-indicators/{symbol}", # Full path: /api/v1/market/ohlcv-with-indicators/{symbol}
    response_model=OHLCVWithIndicatorsAndRegimeResponse,
    summary="Get OHLCV Data with Technical Indicators",
    tags=["Market Data", "Technical Analysis"]
)
async def get_ohlcv_data_with_indicators(
    symbol: str,
    timeframe: str = Query("1h", description="Timeframe string (e.g., '1m', '5m', '1h', '1d')"),
    since: Optional[int] = Query(None, description="Fetch OHLCV since this timestamp (milliseconds UTC)"),
    limit: Optional[int] = Query(100, description="Number of OHLCV candles to fetch (default 100)"),
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client)
):
    """
    Fetches OHLCV data, calculates comprehensive technical indicators, determines detailed market regime,
    and returns all data in a structured response.
    
    - **symbol**: Trading pair symbol (e.g., 'BTC/USDT:USDT')  
    - **timeframe**: Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d, etc.)
    - **since**: Start timestamp in milliseconds UTC (optional)
    - **limit**: Maximum number of candles to fetch (default 100)
    
    Returns OHLCV data enhanced with technical indicators (RSI, MACD, Bollinger Bands, etc.)
    and current market regime analysis (trending, ranging, volatile, etc.).
    """
    if not symbol:
        logger.warning("Symbol parameter missing for /ohlcv-with-indicators endpoint")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Symbol parameter is required.")

    logger.info(f"Request received for OHLCV with indicators & regime: {symbol}, TF: {timeframe}, Limit: {limit}, Since: {since}")
    
    ohlcv_list = []
    try:
        logger.debug(f"Attempting to fetch OHLCV for {symbol}...")
        ohlcv_list = await kucoin_client.fetch_ohlcv(
            symbol=symbol, timeframe=timeframe, since=since, limit=limit
        )
        if ohlcv_list is None:
            logger.warning(f"OHLCV data fetch returned None for {symbol}.")
            return OHLCVWithIndicatorsAndRegimeResponse(
                market_regime=MarketRegimeInfo(descriptive_label="ERROR_FETCHING_OHLCV"),
                data=[]
            )
        if not ohlcv_list:
            logger.info(f"No OHLCV data returned for {symbol} for the given period.")
            return OHLCVWithIndicatorsAndRegimeResponse(
                market_regime=MarketRegimeInfo(descriptive_label="UNCERTAIN_NO_DATA"),
                data=[]
            )
        logger.info(f"Fetched {len(ohlcv_list)} OHLCV candles for {symbol}.")
    except HTTPException as http_exc:
        logger.error(f"HTTPException during OHLCV fetch for {symbol}: {http_exc.detail}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected exception during OHLCV fetch for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch OHLCV for {symbol}: {str(e)}")

    df_with_indicators: Optional[pd.DataFrame] = None
    try:
        logger.debug(f"Calculating indicators for {symbol} with {len(ohlcv_list)} candles...")
        df_with_indicators = calculate_indicators(ohlcv_list)
        
        if df_with_indicators is None:
            logger.error(f"Indicator calculation returned None for {symbol}.")
            return OHLCVWithIndicatorsAndRegimeResponse(
                market_regime=MarketRegimeInfo(descriptive_label="ERROR_INDICATOR_CALC_NONE"),
                data=[]
            )
        if df_with_indicators.empty:
            logger.warning(f"Indicator calculation returned an empty DataFrame for {symbol}.")
            return OHLCVWithIndicatorsAndRegimeResponse(
                market_regime=MarketRegimeInfo(descriptive_label="UNCERTAIN_EMPTY_INDICATORS"),
                data=[]
            )
        logger.info(f"Indicators calculated for {symbol}. Shape: {df_with_indicators.shape}")
    except Exception as e:
        logger.error(f"Exception during indicator calculation for {symbol}: {e}", exc_info=True)
        return OHLCVWithIndicatorsAndRegimeResponse(
            market_regime=MarketRegimeInfo(descriptive_label="ERROR_INDICATOR_CALC_EXCEPTION"),
            data=[]
        )

    market_regime_info_obj = MarketRegimeInfo(descriptive_label="UNCERTAIN_REGIME_INIT_FAILED")
    try:
        logger.debug(f"Determining market regime for {symbol}...")
        market_regime_info_obj = determine_market_regime(df_with_indicators)
        logger.info(f"Determined market regime for {symbol}: {market_regime_info_obj.descriptive_label}")
    except Exception as e:
        logger.error(f"Exception during market regime determination for {symbol}: {e}", exc_info=True)
        # Continue with default error regime

    records: List[Dict[str, Any]] = []
    try:
        logger.debug(f"Converting DataFrame with indicators to dict for {symbol}...")
        df_cleaned = df_with_indicators.replace({pd.NA: None, np.nan: None, pd.NaT: None})
        records = df_cleaned.to_dict(orient='records')
        logger.info(f"Successfully converted DataFrame to dict for {symbol}. Records: {len(records)}")
    except Exception as e:
        logger.error(f"Error serializing indicator data to JSON for {symbol}: {e}", exc_info=True)
        market_regime_info_obj = MarketRegimeInfo(descriptive_label="ERROR_SERIALIZATION")

    return OHLCVWithIndicatorsAndRegimeResponse(market_regime=market_regime_info_obj, data=records)

# ============================================================================
# WEBSOCKET & LOGGING ENDPOINTS
# ============================================================================

async def broadcast_analysis_log(log_entry: Dict[str, Any]):
    """
    Broadcasts a new analysis log entry to all active WebSocket clients.
    """
    disconnected_connections = []
    for connection in active_connections:
        try:
            await connection.send_text(json.dumps(log_entry))
        except WebSocketDisconnect:
            logger.warning(f"WebSocket client disconnected during broadcast.")
            disconnected_connections.append(connection)
        except Exception as e:
            logger.error(f"Error broadcasting analysis log to WebSocket client: {e}", exc_info=True)
            disconnected_connections.append(connection)
    
    # Remove disconnected clients
    for connection in disconnected_connections:
        if connection in active_connections:
            active_connections.remove(connection)
    
    if disconnected_connections:
        logger.info(f"Removed {len(disconnected_connections)} disconnected WebSocket clients. Remaining: {len(active_connections)}")

@router.websocket("/ws/analysis-logs") # Full path: /api/ws/analysis-logs
async def websocket_analysis_logs(websocket: WebSocket):
    """
    WebSocket endpoint for real-time analysis logs.
    Clients connect here to receive live updates from the bot engine during strategy execution.
    
    The bot engine publishes analysis logs via the internal-publish endpoint,
    which are then broadcasted to all connected WebSocket clients.
    """
    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"New WebSocket connection established for analysis logs. Total active: {len(active_connections)}")
    
    try:
        while True:
            await asyncio.sleep(60)  # Keep connection alive
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from analysis logs.")
    except Exception as e:
        logger.error(f"WebSocket error for analysis logs: {e}", exc_info=True)
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)
            logger.info(f"WebSocket connection closed for analysis logs. Total active: {len(active_connections)}")

@router.post(
    "/analysis-logs/internal-publish", # Full path: /api/internal/analysis-logs/internal-publish
    status_code=status.HTTP_202_ACCEPTED,
    summary="Internal Analysis Log Publisher",
    tags=["Internal"]
)
async def internal_publish_analysis_log(
    log_entry: AnalysisLogEntry,
    request: Request
):
    """
    Internal API endpoint for bot_engine to publish analysis logs.
    These logs are then broadcasted to active WebSocket clients.
    Only accepts POST requests from trusted internal sources (e.g., localhost).
    
    **This is an internal endpoint - not for external API consumption.**
    """
    client_host = request.client.host
    if client_host != "127.0.0.1" and client_host != "localhost":
        logger.warning(f"Rejected internal-publish request from untrusted host: {client_host}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Internal endpoint.")

    logger.info(f"Received analysis log from bot_engine: {log_entry.message}")
    await broadcast_analysis_log(log_entry.model_dump())

    return {"status": "success", "message": "Log received and broadcasted."}
