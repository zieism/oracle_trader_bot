# app/indicators/technical_indicators.py
import numpy as np
# Monkey patch for pandas-ta (already at the top of this file from previous versions)
if not hasattr(np, 'NaN'): 
    if hasattr(np, 'nan'): 
        print("Applying monkey patch for numpy.NaN to numpy.nan for pandas-ta compatibility.")
        setattr(np, 'NaN', np.nan)

import pandas as pd
import pandas_ta as ta # type: ignore 
from typing import List, Dict, Any, Optional

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
    bbands_std_dev: float = 2.0, # Changed to float
    # ATR Parameters
    atr_period: int = 14,
    # Volume MA Parameters
    vol_sma_period: int = 20,
    # ADX Parameters
    adx_period: int = 14
) -> Optional[pd.DataFrame]:
    """
    Calculates various technical indicators based on OHLCV data and configurable parameters.
    OHLCV data is expected in CCXT format: [timestamp, open, high, low, close, volume]
    Column names for indicators will reflect the provided periods.
    """
    # Determine minimum data points needed based on longest period
    min_data_points_needed = max(
        ema_slow_period, rsi_period, macd_slow_period + macd_signal_period, 
        bbands_period, atr_period, vol_sma_period, adx_period, 20 # General fallback
    )

    if not ohlcv_data or len(ohlcv_data) < min_data_points_needed: 
        print(f"Indicators: Insufficient OHLCV data (need at least {min_data_points_needed}, got {len(ohlcv_data)}).")
        return None

    df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    try:
        df['open'] = pd.to_numeric(df['open'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['close'] = pd.to_numeric(df['close'])
        df['volume'] = pd.to_numeric(df['volume'])
    except Exception as e:
        print(f"Indicators: Error converting OHLCV columns to numeric: {e}")
        return None

    if df.empty or df['close'].isnull().all(): 
        print("Indicators: DataFrame is empty or 'close' prices are all NaN after conversion.")
        return None
    
    if df['close'].dropna().count() < min_data_points_needed: 
        print(f"Indicators: Insufficient non-NaN close price data points ({df['close'].dropna().count()}) for calculation (need {min_data_points_needed}).")
        return None

    # --- Calculate Indicators using pandas_ta with dynamic column names ---
    try:
        df.ta.ema(length=ema_fast_period, append=True, col_names=(f'EMA_{ema_fast_period}')) 
        df.ta.ema(length=ema_medium_period, append=True, col_names=(f'EMA_{ema_medium_period}')) 
        df.ta.ema(length=ema_slow_period, append=True, col_names=(f'EMA_{ema_slow_period}')) 
    except Exception as e: print(f"Indicators: Error calculating EMAs: {e}")

    try:
        df.ta.rsi(length=rsi_period, append=True, col_names=(f'RSI_{rsi_period}'))
    except Exception as e: print(f"Indicators: Error calculating RSI: {e}")

    try:
        macd_results = df.ta.macd(fast=macd_fast_period, slow=macd_slow_period, signal=macd_signal_period)
        if macd_results is not None and not macd_results.empty and macd_results.shape[1] >=3:
            # Standard MACD column names from pandas_ta are like MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
            # We will use these directly or map them if needed.
            # Let's use dynamic names based on parameters for consistency
            df[f'MACD_{macd_fast_period}_{macd_slow_period}_{macd_signal_period}'] = macd_results.iloc[:,0]
            df[f'MACDh_{macd_fast_period}_{macd_slow_period}_{macd_signal_period}'] = macd_results.iloc[:,1]
            df[f'MACDs_{macd_fast_period}_{macd_slow_period}_{macd_signal_period}'] = macd_results.iloc[:,2]
        else:
            print(f"Indicators: MACD calculation (f:{macd_fast_period},s:{macd_slow_period},sig:{macd_signal_period}) did not return expected columns.")
            df[f'MACD_{macd_fast_period}_{macd_slow_period}_{macd_signal_period}'] = pd.NA
            df[f'MACDh_{macd_fast_period}_{macd_slow_period}_{macd_signal_period}'] = pd.NA
            df[f'MACDs_{macd_fast_period}_{macd_slow_period}_{macd_signal_period}'] = pd.NA
    except Exception as e: print(f"Indicators: Error calculating MACD: {e}")

    try:
        bbands_results = df.ta.bbands(length=bbands_period, std=bbands_std_dev)
        if bbands_results is not None and not bbands_results.empty and bbands_results.shape[1] >= 3:
            # pandas_ta bbands col names are like BBL_20_2.0, BBM_20_2.0, BBU_20_2.0, BBB_20_2.0, BBP_20_2.0
            # We will use dynamic names.
            std_dev_str = str(bbands_std_dev).replace('.', '_') # e.g., 2.0 -> 2_0
            df[f'BBL_{bbands_period}_{std_dev_str}'] = bbands_results.iloc[:,0] 
            df[f'BBM_{bbands_period}_{std_dev_str}'] = bbands_results.iloc[:,1] 
            df[f'BBU_{bbands_period}_{std_dev_str}'] = bbands_results.iloc[:,2] 
            if bbands_results.shape[1] > 3: 
                df[f'BBB_{bbands_period}_{std_dev_str}'] = bbands_results.iloc[:,3] 
            if bbands_results.shape[1] > 4: 
                df[f'BBP_{bbands_period}_{std_dev_str}'] = bbands_results.iloc[:,4] 
        else:
            print(f"Indicators: Bollinger Bands (l:{bbands_period},s:{bbands_std_dev}) did not return expected columns.")
    except Exception as e: print(f"Indicators: Error calculating Bollinger Bands: {e}")

    try:
        df.ta.atr(length=atr_period, append=True, col_names=(f'ATR_{atr_period}'))
    except Exception as e: print(f"Indicators: Error calculating ATR: {e}")

    try:
        df.ta.obv(append=True, col_names=('OBV')) # OBV usually doesn't take period
    except Exception as e: print(f"Indicators: Error calculating OBV: {e}")
        
    if 'volume' in df.columns:
        try:
            df[f'VOL_SMA_{vol_sma_period}'] = df['volume'].rolling(window=vol_sma_period, min_periods=1).mean()
        except Exception as e: print(f"Indicators: Error calculating Volume SMA: {e}")

    try:
        adx_results = df.ta.adx(length=adx_period)
        if adx_results is not None and not adx_results.empty and adx_results.shape[1] >=1:
            # ADX columns from pandas_ta are like ADX_14, DMP_14, DMN_14
            df[f'ADX_{adx_period}'] = adx_results.iloc[:,0] 
            if adx_results.shape[1] > 1: 
                df[f'DMP_{adx_period}'] = adx_results.iloc[:,1] 
            if adx_results.shape[1] > 2: 
                df[f'DMN_{adx_period}'] = adx_results.iloc[:,2] 
        else:
            print(f"Indicators: ADX (l:{adx_period}) did not return expected columns.")
    except Exception as e: print(f"Indicators: Error calculating ADX: {e}")
        
    return df