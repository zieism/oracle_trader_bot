# backend/app/indicators/technical_indicators.py
"""
Technical Indicators Module

Professional implementation of technical analysis indicators using pandas-ta.
Provides comprehensive indicator calculations with configurable parameters.
"""
import numpy as np
import pandas as pd
import pandas_ta as ta  # type: ignore 
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Monkey patch for pandas-ta numpy compatibility
if not hasattr(np, 'NaN'): 
    if hasattr(np, 'nan'): 
        logger.info("Applying monkey patch for numpy.NaN to numpy.nan for pandas-ta compatibility")
        setattr(np, 'NaN', np.nan)

def calculate_indicators(
    ohlcv_data: List[List[Any]],
    # EMA Parameters
    ema_fast_period: int = 10,
    ema_medium_period: int = 20,
    ema_slow_period: int = 50,
    # RSI Parameters
    rsi_period: int = 14,
    # MACD Parameters
    macd_fast_period: int = 12,
    macd_slow_period: int = 26,
    macd_signal_period: int = 9,
    # Bollinger Bands Parameters
    bbands_period: int = 20,
    bbands_std_dev: float = 2.0,
    # ATR Parameters
    atr_period: int = 14,
    # Volume MA Parameters
    vol_sma_period: int = 20,
    # ADX Parameters
    adx_period: int = 14
) -> Optional[pd.DataFrame]:
    """
    Calculate comprehensive technical indicators based on OHLCV data.
    
    Processes CCXT format OHLCV data: [timestamp, open, high, low, close, volume]
    and calculates various technical indicators with configurable parameters.
    
    Args:
        ohlcv_data: List of OHLCV candlestick data in CCXT format
        ema_fast_period: Fast EMA period (default: 10)
        ema_medium_period: Medium EMA period (default: 20)
        ema_slow_period: Slow EMA period (default: 50)
        rsi_period: RSI calculation period (default: 14)
        macd_fast_period: MACD fast EMA period (default: 12)
        macd_slow_period: MACD slow EMA period (default: 26)
        macd_signal_period: MACD signal line period (default: 9)
        bbands_period: Bollinger Bands period (default: 20)
        bbands_std_dev: Bollinger Bands standard deviation multiplier (default: 2.0)
        atr_period: ATR calculation period (default: 14)
        vol_sma_period: Volume SMA period (default: 20)
        adx_period: ADX calculation period (default: 14)
        
    Returns:
        DataFrame with OHLCV data and calculated indicators, or None if insufficient data
        
    Column naming convention:
        - EMA_{period}: Exponential Moving Average
        - RSI_{period}: Relative Strength Index
        - MACD_{fast}_{slow}_{signal}: MACD Line
        - MACDs_{fast}_{slow}_{signal}: MACD Signal Line
        - MACDh_{fast}_{slow}_{signal}: MACD Histogram
        - BBL/BBM/BBU_{period}_{std_dev}: Bollinger Bands Lower/Middle/Upper
        - ATR_{period}: Average True Range
        - ADX_{period}: Average Directional Index
        - DMP/DMN_{period}: Directional Movement Positive/Negative
        - VOL_SMA_{period}: Volume Simple Moving Average
        - OBV: On Balance Volume
    """
    # Determine minimum data points needed
    min_data_points_needed = max(
        ema_slow_period, rsi_period, macd_slow_period + macd_signal_period, 
        bbands_period, atr_period, vol_sma_period, adx_period, 20  # General fallback
    )

    if not ohlcv_data or len(ohlcv_data) < min_data_points_needed: 
        logger.warning(f"Indicators: Insufficient OHLCV data (need at least {min_data_points_needed}, got {len(ohlcv_data)})")
        return None

    # Create DataFrame from OHLCV data
    df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # Convert price columns to numeric
    try:
        price_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in price_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    except Exception as e:
        logger.error(f"Indicators: Error converting OHLCV columns to numeric: {e}")
        return None

    # Validate data quality
    if df.empty or df['close'].isnull().all(): 
        logger.error("Indicators: DataFrame is empty or all close prices are NaN")
        return None
    
    if df['close'].dropna().count() < min_data_points_needed: 
        logger.warning(f"Indicators: Insufficient non-NaN close price data ({df['close'].dropna().count()}) for calculation (need {min_data_points_needed})")
        return None

    # Calculate Exponential Moving Averages
    try:
        df.ta.ema(length=ema_fast_period, append=True, col_names=(f'EMA_{ema_fast_period}')) 
        df.ta.ema(length=ema_medium_period, append=True, col_names=(f'EMA_{ema_medium_period}')) 
        df.ta.ema(length=ema_slow_period, append=True, col_names=(f'EMA_{ema_slow_period}'))
        logger.debug(f"Calculated EMAs: {ema_fast_period}, {ema_medium_period}, {ema_slow_period}")
    except Exception as e: 
        logger.error(f"Indicators: Error calculating EMAs: {e}")

    # Calculate Relative Strength Index
    try:
        df.ta.rsi(length=rsi_period, append=True, col_names=(f'RSI_{rsi_period}'))
        logger.debug(f"Calculated RSI with period {rsi_period}")
    except Exception as e: 
        logger.error(f"Indicators: Error calculating RSI: {e}")

    # Calculate MACD
    try:
        macd_results = df.ta.macd(fast=macd_fast_period, slow=macd_slow_period, signal=macd_signal_period)
        if macd_results is not None and not macd_results.empty and macd_results.shape[1] >= 3:
            # Map results to consistent column names
            df[f'MACD_{macd_fast_period}_{macd_slow_period}_{macd_signal_period}'] = macd_results.iloc[:, 0]
            df[f'MACDh_{macd_fast_period}_{macd_slow_period}_{macd_signal_period}'] = macd_results.iloc[:, 1]
            df[f'MACDs_{macd_fast_period}_{macd_slow_period}_{macd_signal_period}'] = macd_results.iloc[:, 2]
            logger.debug(f"Calculated MACD ({macd_fast_period}/{macd_slow_period}/{macd_signal_period})")
        else:
            logger.warning(f"MACD calculation failed - setting NaN values")
            df[f'MACD_{macd_fast_period}_{macd_slow_period}_{macd_signal_period}'] = pd.NA
            df[f'MACDh_{macd_fast_period}_{macd_slow_period}_{macd_signal_period}'] = pd.NA
            df[f'MACDs_{macd_fast_period}_{macd_slow_period}_{macd_signal_period}'] = pd.NA
    except Exception as e: 
        logger.error(f"Indicators: Error calculating MACD: {e}")

    # Calculate Bollinger Bands
    try:
        bbands_results = df.ta.bbands(length=bbands_period, std=bbands_std_dev)
        if bbands_results is not None and not bbands_results.empty and bbands_results.shape[1] >= 3:
            # Create standardized column names
            std_dev_str = str(bbands_std_dev).replace('.', '_')  # e.g., 2.0 -> 2_0
            df[f'BBL_{bbands_period}_{std_dev_str}'] = bbands_results.iloc[:, 0]  # Lower Band
            df[f'BBM_{bbands_period}_{std_dev_str}'] = bbands_results.iloc[:, 1]  # Middle Band
            df[f'BBU_{bbands_period}_{std_dev_str}'] = bbands_results.iloc[:, 2]  # Upper Band
            
            # Additional Bollinger Band metrics if available
            if bbands_results.shape[1] > 3: 
                df[f'BBB_{bbands_period}_{std_dev_str}'] = bbands_results.iloc[:, 3]  # Bandwidth
            if bbands_results.shape[1] > 4: 
                df[f'BBP_{bbands_period}_{std_dev_str}'] = bbands_results.iloc[:, 4]  # %B Position
                
            logger.debug(f"Calculated Bollinger Bands ({bbands_period}, {bbands_std_dev})")
        else:
            logger.warning(f"Bollinger Bands calculation failed for period {bbands_period}")
    except Exception as e: 
        logger.error(f"Indicators: Error calculating Bollinger Bands: {e}")

    # Calculate Average True Range
    try:
        df.ta.atr(length=atr_period, append=True, col_names=(f'ATR_{atr_period}'))
        logger.debug(f"Calculated ATR with period {atr_period}")
    except Exception as e: 
        logger.error(f"Indicators: Error calculating ATR: {e}")

    # Calculate On Balance Volume
    try:
        df.ta.obv(append=True, col_names=('OBV'))
        logger.debug("Calculated On Balance Volume")
    except Exception as e: 
        logger.error(f"Indicators: Error calculating OBV: {e}")
        
    # Calculate Volume Simple Moving Average
    if 'volume' in df.columns:
        try:
            df[f'VOL_SMA_{vol_sma_period}'] = df['volume'].rolling(
                window=vol_sma_period, min_periods=1
            ).mean()
            logger.debug(f"Calculated Volume SMA with period {vol_sma_period}")
        except Exception as e: 
            logger.error(f"Indicators: Error calculating Volume SMA: {e}")

    # Calculate Average Directional Index (ADX)
    try:
        adx_results = df.ta.adx(length=adx_period)
        if adx_results is not None and not adx_results.empty and adx_results.shape[1] >= 1:
            # Map ADX results to consistent column names
            df[f'ADX_{adx_period}'] = adx_results.iloc[:, 0]  # ADX
            if adx_results.shape[1] > 1: 
                df[f'DMP_{adx_period}'] = adx_results.iloc[:, 1]  # DI+
            if adx_results.shape[1] > 2: 
                df[f'DMN_{adx_period}'] = adx_results.iloc[:, 2]  # DI-
            logger.debug(f"Calculated ADX with period {adx_period}")
        else:
            logger.warning(f"ADX calculation failed for period {adx_period}")
    except Exception as e: 
        logger.error(f"Indicators: Error calculating ADX: {e}")
    
    logger.info(f"Technical indicators calculated successfully. DataFrame shape: {df.shape}")
    return df
