# app/analysis/market_regime.py
import pandas as pd
import numpy as np
from typing import Optional
import logging # Import logging module

from app.schemas.market_regime_schemas import MarketRegimeInfo 

# Get a logger for this module
logger = logging.getLogger(__name__)
# You can set a specific level for this logger if needed, e.g., logger.setLevel(logging.DEBUG)
# However, the root logger configuration in bot_engine.py should generally cover this.

# Constants for regime labels
REGIME_TRENDING_UP = "TRENDING_UP"
REGIME_TRENDING_DOWN = "TRENDING_DOWN"
REGIME_RANGING = "RANGING"
REGIME_UNCERTAIN = "UNCERTAIN"

def determine_market_regime(
    df_with_indicators: pd.DataFrame,
    adx_period: int,
    adx_weak_trend_threshold: float,
    adx_strong_trend_threshold: float,
    bbands_period_for_bbw: int, 
    bbands_std_dev_for_bbw: float, 
    bbw_low_threshold: float, 
    bbw_high_threshold: float
) -> MarketRegimeInfo:
    """
    Determines the current market regime with more details, using configurable thresholds
    and dynamically constructed indicator column names.
    """
    default_regime = MarketRegimeInfo(
        trend_direction="SIDEWAYS", 
        volatility_level="NORMAL", # Default if cannot be determined
        descriptive_label="UNCERTAIN_NO_DATA"
    )

    if df_with_indicators is None or df_with_indicators.empty:
        logger.warning("MarketRegime: Input DataFrame is None or empty.")
        return default_regime

    # Ensure there's at least one row of data
    if len(df_with_indicators) < 1:
        logger.warning("MarketRegime: Input DataFrame has no rows.")
        return default_regime
        
    latest_indicators = df_with_indicators.iloc[-1]

    adx_col_name = f'ADX_{adx_period}'
    plus_di_col_name = f'DMP_{adx_period}'
    minus_di_col_name = f'DMN_{adx_period}'
    
    std_dev_str_for_bbw = str(bbands_std_dev_for_bbw).replace('.', '_')
    bbw_col_name = f'BBB_{bbands_period_for_bbw}_{std_dev_str_for_bbw}'

    adx = latest_indicators.get(adx_col_name)
    plus_di = latest_indicators.get(plus_di_col_name)
    minus_di = latest_indicators.get(minus_di_col_name)
    bbw = latest_indicators.get(bbw_col_name)

    # --- Added debug log for BBW values ---
    logger.info(
        f"MarketRegimeDebug: BBW Value from DF (col:'{bbw_col_name}'): {bbw}, "
        f"Configured BBW_HIGH_THRESHOLD: {bbw_high_threshold}, "
        f"Configured BBW_LOW_THRESHOLD: {bbw_low_threshold}"
    )
    # -----------------------------------------

    regime_info = MarketRegimeInfo(
        trend_direction="SIDEWAYS", # Default
        volatility_level="NORMAL",  # Default if BBW is NaN or not processed
        descriptive_label=REGIME_UNCERTAIN, 
        trend_strength_adx = float(adx) if pd.notna(adx) else None,
        plus_di = float(plus_di) if pd.notna(plus_di) else None,
        minus_di = float(minus_di) if pd.notna(minus_di) else None,
        bbw_value = float(bbw) if pd.notna(bbw) else None
    )
    
    descriptive_parts = []

    # 1. Determine Volatility Level
    if pd.notna(bbw): # Only proceed if BBW is a valid number
        if bbw < bbw_low_threshold:
            regime_info.volatility_level = "LOW"
            descriptive_parts.append("Low Volatility")
        elif bbw > bbw_high_threshold:
            regime_info.volatility_level = "HIGH"
            descriptive_parts.append("High Volatility")
        else:
            regime_info.volatility_level = "NORMAL"
            descriptive_parts.append("Normal Volatility")
    else:
        descriptive_parts.append(f"Volatility Undetermined (BBW from column '{bbw_col_name}' is N/A or missing)")
        # Keep default volatility_level="NORMAL" in regime_info or set to None
        regime_info.volatility_level = None # Explicitly set to None if BBW is N/A


    # 2. Determine Trend Direction and Strength
    if pd.notna(adx) and pd.notna(plus_di) and pd.notna(minus_di):
        if adx > adx_strong_trend_threshold:
            regime_info.is_trending = True
            regime_info.is_strongly_trending = True
            if plus_di > minus_di:
                regime_info.trend_direction = "UP"
                descriptive_parts.append("Strong Bull Trend")
            else: # minus_di >= plus_di
                regime_info.trend_direction = "DOWN"
                descriptive_parts.append("Strong Bear Trend")
        elif adx > adx_weak_trend_threshold:
            regime_info.is_trending = True
            regime_info.is_strongly_trending = False
            if plus_di > minus_di:
                regime_info.trend_direction = "UP"
                descriptive_parts.append("Weak Bull Trend")
            else:
                regime_info.trend_direction = "DOWN"
                descriptive_parts.append("Weak Bear Trend")
        else: # ADX is low
            regime_info.is_trending = False
            regime_info.is_strongly_trending = False
            regime_info.trend_direction = "SIDEWAYS"
            descriptive_parts.append("Ranging/Sideways")
    else:
        descriptive_parts.append(f"Trend Undetermined (ADX/DI from column '{adx_col_name}' N/A or missing)")
        regime_info.trend_direction = "SIDEWAYS" # Default if ADX components are missing

    # Construct the final descriptive label
    if not descriptive_parts or all(p.startswith("Volatility Undetermined") and p.startswith("Trend Undetermined") for p in descriptive_parts) :
        regime_info.descriptive_label = REGIME_UNCERTAIN
    else:
        trend_part = [p for p in descriptive_parts if "Trend" in p or "Ranging" in p or "Sideways" in p]
        vol_part = [p for p in descriptive_parts if "Volatility" in p]
        
        final_label_parts = []
        if trend_part: final_label_parts.extend(trend_part)
        if vol_part: final_label_parts.extend(vol_part)
        
        if final_label_parts:
            regime_info.descriptive_label = ", ".join(final_label_parts)
        else: # Fallback if all parts were filtered out for some reason
            regime_info.descriptive_label = REGIME_UNCERTAIN
            
    return regime_info
