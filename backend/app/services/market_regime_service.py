# backend/app/services/market_regime_service.py
"""
Market Regime Analysis Service

Professional market regime determination using ADX trend strength analysis
and Bollinger Band Width volatility assessment.
"""
import pandas as pd
import numpy as np
import logging
from typing import Optional

from app.schemas.market_regime_schemas import MarketRegimeInfo 

logger = logging.getLogger(__name__)

# Regime classification constants
REGIME_TRENDING_UP = "TRENDING_UP"
REGIME_TRENDING_DOWN = "TRENDING_DOWN"
REGIME_RANGING = "RANGING"
REGIME_UNCERTAIN = "UNCERTAIN"

def determine_market_regime(
    df_with_indicators: pd.DataFrame,
    adx_period: int = 14,
    adx_weak_trend_threshold: float = 25.0,
    adx_strong_trend_threshold: float = 50.0,
    bbands_period_for_bbw: int = 20, 
    bbands_std_dev_for_bbw: float = 2.0, 
    bbw_low_threshold: float = 0.1, 
    bbw_high_threshold: float = 0.3
) -> MarketRegimeInfo:
    """
    Determine the current market regime with detailed analysis.
    
    Uses ADX (Average Directional Index) for trend strength and direction,
    and Bollinger Band Width for volatility assessment.
    
    Args:
        df_with_indicators: DataFrame with calculated technical indicators
        adx_period: ADX calculation period (default: 14)
        adx_weak_trend_threshold: Minimum ADX for weak trend (default: 25.0)
        adx_strong_trend_threshold: Minimum ADX for strong trend (default: 50.0)
        bbands_period_for_bbw: Bollinger Bands period for width calculation (default: 20)
        bbands_std_dev_for_bbw: Bollinger Bands standard deviation (default: 2.0)
        bbw_low_threshold: Threshold for low volatility (default: 0.1)
        bbw_high_threshold: Threshold for high volatility (default: 0.3)
        
    Returns:
        MarketRegimeInfo containing regime classification and supporting metrics
        
    Market Regime Classification:
        - TRENDING_UP: Strong upward trend with ADX > threshold and DI+ > DI-
        - TRENDING_DOWN: Strong downward trend with ADX > threshold and DI- > DI+
        - RANGING: Low ADX indicating sideways/ranging market
        - UNCERTAIN: Unable to determine due to missing data
        
    Volatility Classification:
        - LOW: BBW < low_threshold (tight price action)
        - NORMAL: BBW between thresholds (typical volatility)
        - HIGH: BBW > high_threshold (expanded price action)
    """
    default_regime = MarketRegimeInfo(
        trend_direction="SIDEWAYS", 
        volatility_level="NORMAL",
        descriptive_label="UNCERTAIN_NO_DATA"
    )

    # Validate input data
    if df_with_indicators is None or df_with_indicators.empty:
        logger.warning("MarketRegime: Input DataFrame is None or empty")
        return default_regime

    if len(df_with_indicators) < 1:
        logger.warning("MarketRegime: Input DataFrame has no rows")
        return default_regime
        
    latest_indicators = df_with_indicators.iloc[-1]

    # Construct indicator column names based on parameters
    adx_col_name = f'ADX_{adx_period}'
    plus_di_col_name = f'DMP_{adx_period}'
    minus_di_col_name = f'DMN_{adx_period}'
    
    std_dev_str_for_bbw = str(bbands_std_dev_for_bbw).replace('.', '_')
    bbw_col_name = f'BBB_{bbands_period_for_bbw}_{std_dev_str_for_bbw}'

    # Extract indicator values
    adx = latest_indicators.get(adx_col_name)
    plus_di = latest_indicators.get(plus_di_col_name)
    minus_di = latest_indicators.get(minus_di_col_name)
    bbw = latest_indicators.get(bbw_col_name)

    logger.debug(f"MarketRegime indicators - ADX: {adx}, +DI: {plus_di}, -DI: {minus_di}, BBW: {bbw}")
    logger.debug(f"MarketRegime thresholds - ADX weak: {adx_weak_trend_threshold}, "
                 f"ADX strong: {adx_strong_trend_threshold}, BBW low: {bbw_low_threshold}, BBW high: {bbw_high_threshold}")

    # Initialize regime info with defaults
    regime_info = MarketRegimeInfo(
        trend_direction="SIDEWAYS",
        volatility_level="NORMAL",
        descriptive_label=REGIME_UNCERTAIN, 
        trend_strength_adx=float(adx) if pd.notna(adx) else None,
        plus_di=float(plus_di) if pd.notna(plus_di) else None,
        minus_di=float(minus_di) if pd.notna(minus_di) else None,
        bbw_value=float(bbw) if pd.notna(bbw) else None
    )
    
    descriptive_parts = []

    # 1. Analyze Volatility Level using Bollinger Band Width
    if pd.notna(bbw):
        if bbw < bbw_low_threshold:
            regime_info.volatility_level = "LOW"
            descriptive_parts.append("Low Volatility")
            logger.debug(f"MarketRegime: Low volatility detected (BBW: {bbw:.4f} < {bbw_low_threshold})")
        elif bbw > bbw_high_threshold:
            regime_info.volatility_level = "HIGH"
            descriptive_parts.append("High Volatility")
            logger.debug(f"MarketRegime: High volatility detected (BBW: {bbw:.4f} > {bbw_high_threshold})")
        else:
            regime_info.volatility_level = "NORMAL"
            descriptive_parts.append("Normal Volatility")
            logger.debug(f"MarketRegime: Normal volatility detected (BBW: {bbw:.4f})")
    else:
        descriptive_parts.append(f"Volatility Undetermined (BBW from '{bbw_col_name}' is N/A)")
        regime_info.volatility_level = None
        logger.warning(f"MarketRegime: BBW value is NaN from column '{bbw_col_name}'")

    # 2. Analyze Trend Direction and Strength using ADX and Directional Movement
    if pd.notna(adx) and pd.notna(plus_di) and pd.notna(minus_di):
        if adx > adx_strong_trend_threshold:
            # Strong trending market
            regime_info.is_trending = True
            regime_info.is_strongly_trending = True
            if plus_di > minus_di:
                regime_info.trend_direction = "UP"
                descriptive_parts.append("Strong Bull Trend")
                logger.info(f"MarketRegime: Strong uptrend detected (ADX: {adx:.2f}, +DI: {plus_di:.2f} > -DI: {minus_di:.2f})")
            else:
                regime_info.trend_direction = "DOWN"
                descriptive_parts.append("Strong Bear Trend")
                logger.info(f"MarketRegime: Strong downtrend detected (ADX: {adx:.2f}, -DI: {minus_di:.2f} > +DI: {plus_di:.2f})")
        elif adx > adx_weak_trend_threshold:
            # Weak trending market
            regime_info.is_trending = True
            regime_info.is_strongly_trending = False
            if plus_di > minus_di:
                regime_info.trend_direction = "UP"
                descriptive_parts.append("Weak Bull Trend")
                logger.info(f"MarketRegime: Weak uptrend detected (ADX: {adx:.2f}, +DI: {plus_di:.2f} > -DI: {minus_di:.2f})")
            else:
                regime_info.trend_direction = "DOWN"
                descriptive_parts.append("Weak Bear Trend")
                logger.info(f"MarketRegime: Weak downtrend detected (ADX: {adx:.2f}, -DI: {minus_di:.2f} > +DI: {plus_di:.2f})")
        else:
            # Ranging/sideways market
            regime_info.is_trending = False
            regime_info.is_strongly_trending = False
            regime_info.trend_direction = "SIDEWAYS"
            descriptive_parts.append("Ranging/Sideways")
            logger.info(f"MarketRegime: Ranging market detected (ADX: {adx:.2f} < {adx_weak_trend_threshold})")
    else:
        descriptive_parts.append(f"Trend Undetermined (ADX/DI indicators from '{adx_col_name}' N/A)")
        regime_info.trend_direction = "SIDEWAYS"
        logger.warning(f"MarketRegime: ADX or DI values are NaN - using default sideways trend")

    # 3. Construct final descriptive label
    if not descriptive_parts:
        regime_info.descriptive_label = REGIME_UNCERTAIN
    else:
        # Separate trend and volatility components
        trend_parts = [p for p in descriptive_parts if any(keyword in p for keyword in ["Trend", "Ranging", "Sideways", "Undetermined"])]
        vol_parts = [p for p in descriptive_parts if "Volatility" in p]
        
        final_label_parts = []
        if trend_parts: 
            final_label_parts.extend(trend_parts)
        if vol_parts: 
            final_label_parts.extend(vol_parts)
        
        if final_label_parts:
            regime_info.descriptive_label = ", ".join(final_label_parts)
        else:
            regime_info.descriptive_label = REGIME_UNCERTAIN

    logger.info(f"MarketRegime determined: {regime_info.descriptive_label}")
    return regime_info
