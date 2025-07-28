# app/api/endpoints/market_data.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Any, Optional, Dict 
import logging
import pandas as pd
import numpy as np 

from app.api.dependencies import get_kucoin_client 
from app.exchange_clients.kucoin_futures_client import KucoinFuturesClient
from app.indicators.technical_indicators import calculate_indicators
# ???? ???? ???? ????? ????? ????? ? ??????? ???? ????
from app.analysis.market_regime import determine_market_regime 
from app.schemas.market_regime_schemas import MarketRegimeInfo, OHLCVWithIndicatorsAndRegimeResponse

router = APIRouter()
logger = logging.getLogger(__name__) 
logger.setLevel(logging.DEBUG) 

@router.get("/ohlcv/{symbol}", response_model=List[List[Any]])
async def get_ohlcv_data(
    # ... (??? Endpoint ???? ????? ???? ???????) ...
    symbol: str, 
    timeframe: str = Query("1h", description="Timeframe string (e.g., '1m', '5m', '1h', '1d', '1w', '1M')"),
    since: Optional[int] = Query(None, description="Fetch OHLCV since this timestamp (milliseconds UTC)"),
    limit: Optional[int] = Query(None, description="Number of OHLCV candles to fetch (exchange default if None, max varies)"),
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client)
):
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

# ??????? ?? ??????? ???? ????
@router.get("/ohlcv-with-indicators/{symbol}", response_model=OHLCVWithIndicatorsAndRegimeResponse) 
async def get_ohlcv_data_with_indicators(
    symbol: str, 
    timeframe: str = Query("1h", description="Timeframe string (e.g., '1m', '5m', '1h', '1d')"),
    since: Optional[int] = Query(None, description="Fetch OHLCV since this timestamp (milliseconds UTC)"),
    limit: Optional[int] = Query(100, description="Number of OHLCV candles to fetch (default 100)"),
    kucoin_client: KucoinFuturesClient = Depends(get_kucoin_client)
):
    """
    Fetches OHLCV data, calculates technical indicators, determines detailed market regime,
    and returns all data.
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
            # ???? ?? ???? ?? ????? ?????? ?? ???? ??? ?????? ????
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
                data=[] # ?? ???????? ohlcv_list ????? ?? ?????????
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
            data=[] # ?? ???????? ohlcv_list ????? ?? ?????????
        )

    market_regime_info_obj = MarketRegimeInfo(descriptive_label="UNCERTAIN_REGIME_INIT_FAILED")
    try:
        logger.debug(f"Determining market regime for {symbol}...")
        market_regime_info_obj = determine_market_regime(df_with_indicators)
        logger.info(f"Determined market regime for {symbol}: {market_regime_info_obj.descriptive_label}")
    except Exception as e:
        logger.error(f"Exception during market regime determination for {symbol}: {e}", exc_info=True)
        # ?? ???? ??? ?? ????? ?????? ?????? ????????? ???????? ???? ?? ????????? ?? ?????????
        # ? ?? market_regime_info_obj ??????? ??????? ????

    records: List[Dict[str, Any]] = []
    try:
        logger.debug(f"Converting DataFrame with indicators to dict for {symbol}...")
        df_cleaned = df_with_indicators.replace({pd.NA: None, np.nan: None, pd.NaT: None})
        records = df_cleaned.to_dict(orient='records')
        logger.info(f"Successfully converted DataFrame to dict for {symbol}. Records: {len(records)}")
    except Exception as e:
        logger.error(f"Error serializing indicator data to JSON for {symbol}: {e}", exc_info=True)
        # ??? ?? ??? ????? ??? ?? ???? records ???? ???????
        market_regime_info_obj = MarketRegimeInfo(descriptive_label="ERROR_SERIALIZATION")


    return OHLCVWithIndicatorsAndRegimeResponse(market_regime=market_regime_info_obj, data=records)