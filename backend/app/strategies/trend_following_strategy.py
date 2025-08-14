# backend/app/strategies/trend_following_strategy.py
"""
Trend Following Strategy

Professional implementation of trend-following trading strategy using EMA crossovers,
RSI confirmation, and MACD signals. Designed for trending market conditions.
"""
import pandas as pd
import numpy as np 
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone

from app.schemas.trading_signal import TradingSignal, TradeDirection
from app.schemas.market_regime_schemas import MarketRegimeInfo 
from app.core.config import settings

logger = logging.getLogger(__name__)

def _calculate_trend_leverage(
    signal_strength: float, 
    volatility_level: Optional[str],
    leverage_tiers: List[Tuple[float, int]],
    default_leverage: int
) -> int:
    """
    Determine leverage based on signal strength, volatility, and predefined tiers.
    
    Args:
        signal_strength: Calculated signal strength (0.0-1.0+)
        volatility_level: Market volatility assessment ("LOW", "MEDIUM", "HIGH") 
        leverage_tiers: List of (min_strength, leverage) tuples
        default_leverage: Fallback leverage value
        
    Returns:
        Calculated leverage value
    """
    base_leverage = default_leverage 
    
    # Find the highest leverage tier that the signal strength qualifies for
    applicable_leverages = [lev_val for strength_thresh, lev_val in leverage_tiers if signal_strength >= strength_thresh]
    if applicable_leverages:
        base_leverage = max(applicable_leverages)
    else:
        base_leverage = default_leverage

    # Reduce leverage in high volatility environments
    if volatility_level == "HIGH":
        adjusted_leverage = max(1, base_leverage // 2) 
        logger.info(f"TrendStrategy: Reducing leverage due to HIGH volatility: base={base_leverage} -> adjusted={adjusted_leverage}")
        return adjusted_leverage
        
    return base_leverage

def generate_trend_signal(
    symbol: str,
    df_with_indicators: pd.DataFrame, 
    market_regime_info: MarketRegimeInfo, 
    current_open_positions_symbols: List[str],
    ema_fast_period: int,
    ema_medium_period: int,
    ema_slow_period: int,
    rsi_period: int,
    rsi_overbought: int,
    rsi_oversold: int,
    rsi_bull_zone_min: int,
    rsi_bear_zone_max: int,
    atr_period_sl_tp: int,
    atr_multiplier_sl: float,
    tp_rr_ratio: float,
    min_signal_strength: float,
    leverage_tiers_list: List[Tuple[float, int]],
    default_bot_leverage: int
) -> Optional[TradingSignal]:
    """
    Generate trading signal based on trend-following strategy.
    
    Strategy Logic:
    - LONG signals in trending UP markets with EMA alignment, RSI confirmation, and MACD bullish
    - SHORT signals in trending DOWN markets with EMA alignment, RSI confirmation, and MACD bearish
    - Uses ATR-based stop losses and risk-reward ratio for take profits
    
    Args:
        symbol: Trading symbol to analyze
        df_with_indicators: DataFrame with OHLCV data and calculated indicators
        market_regime_info: Current market regime analysis
        current_open_positions_symbols: List of symbols with open positions
        ema_fast_period: Fast EMA period for trend confirmation
        ema_medium_period: Medium EMA period for trend confirmation  
        ema_slow_period: Slow EMA period for trend confirmation
        rsi_period: RSI calculation period
        rsi_overbought: RSI overbought threshold
        rsi_oversold: RSI oversold threshold
        rsi_bull_zone_min: Minimum RSI for bullish signals
        rsi_bear_zone_max: Maximum RSI for bearish signals
        atr_period_sl_tp: ATR period for stop loss calculation
        atr_multiplier_sl: ATR multiplier for stop loss distance
        tp_rr_ratio: Risk-reward ratio for take profit calculation
        min_signal_strength: Minimum signal strength required
        leverage_tiers_list: Leverage tiers based on signal strength
        default_bot_leverage: Default leverage value
        
    Returns:
        TradingSignal if conditions are met, None otherwise
    """
    # Validate data sufficiency
    min_data_needed = max(ema_slow_period, rsi_period, atr_period_sl_tp, 26+9) 
    if df_with_indicators is None or df_with_indicators.empty or len(df_with_indicators) < min_data_needed:
        logger.warning(f"TrendStrategy ({symbol}): Insufficient data - need {min_data_needed}, have {len(df_with_indicators) if df_with_indicators is not None else 0}")
        return None

    latest_data = df_with_indicators.iloc[-1]

    # Skip if position already open for this symbol
    if symbol in current_open_positions_symbols:
        logger.debug(f"TrendStrategy ({symbol}): Position already open, skipping")
        return None

    # Only generate signals in trending markets
    if not market_regime_info.is_trending:
        logger.debug(f"TrendStrategy ({symbol}): Market not trending, skipping")
        return None
    
    # Initialize signal variables
    signal_direction: Optional[TradeDirection] = None
    entry_price_proposal: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    final_leverage: int = default_bot_leverage
    signal_strength_score: float = 0.0
    
    # Define indicator column names
    ema_fast_col = f'EMA_{ema_fast_period}'
    ema_medium_col = f'EMA_{ema_medium_period}'
    ema_slow_col = f'EMA_{ema_slow_period}'
    rsi_col = f'RSI_{rsi_period}'
    macd_line_col = f'MACD_{settings.TREND_MACD_FAST}_{settings.TREND_MACD_SLOW}_{settings.TREND_MACD_SIGNAL}'
    macd_signal_col = f'MACDs_{settings.TREND_MACD_FAST}_{settings.TREND_MACD_SLOW}_{settings.TREND_MACD_SIGNAL}'
    atr_col = f'ATR_{atr_period_sl_tp}'
    
    # Extract current market data
    current_close = latest_data.get('close')
    current_high = latest_data.get('high')
    current_low = latest_data.get('low')
    ema_fast_val = latest_data.get(ema_fast_col)
    ema_medium_val = latest_data.get(ema_medium_col)
    ema_slow_val = latest_data.get(ema_slow_col)
    rsi_val = latest_data.get(rsi_col)
    macd_line_val = latest_data.get(macd_line_col)
    macd_signal_val = latest_data.get(macd_signal_col)
    current_volume = latest_data.get('volume')
    vol_sma_period_from_indicators = 20
    volume_sma_val = latest_data.get(f'VOL_SMA_{vol_sma_period_from_indicators}')
    atr_val = latest_data.get(atr_col)

    # LONG Signal Logic - Trending UP market
    if market_regime_info.trend_direction == "UP":
        required_values = [current_close, current_low, ema_fast_val, ema_medium_val, ema_slow_val, 
                          rsi_val, macd_line_val, macd_signal_val, atr_val]
        if any(pd.isna(val) for val in required_values):
            logger.warning(f"TrendStrategy ({symbol}): Missing indicator values for LONG signal")
            return None

        # EMA alignment check: Fast > Medium > Slow and price above medium EMA
        if (ema_fast_val > ema_medium_val) and (ema_medium_val > ema_slow_val) and (current_close > ema_medium_val):
            signal_strength_score += 0.4
            
            # MACD bullish confirmation
            if (macd_line_val > macd_signal_val):
                signal_strength_score += 0.3
                
            # RSI in bullish zone but not overbought
            if (rsi_val > rsi_bull_zone_min and rsi_val < rsi_overbought):
                signal_strength_score += 0.3
                
            # Volume confirmation
            if pd.notna(current_volume) and pd.notna(volume_sma_val) and current_volume > volume_sma_val:
                signal_strength_score += 0.1 

            # Generate signal if strength meets threshold
            if signal_strength_score >= min_signal_strength:
                signal_direction = TradeDirection.LONG
                entry_price_proposal = current_close 
                stop_loss_price = current_low - (atr_multiplier_sl * atr_val)
                risk_per_unit = entry_price_proposal - stop_loss_price if pd.notna(entry_price_proposal) and pd.notna(stop_loss_price) else 0.0
                
                if risk_per_unit > 1e-9:
                    take_profit_price = entry_price_proposal + (tp_rr_ratio * risk_per_unit)
                else:
                    take_profit_price = None
                    signal_direction = None 
                    logger.warning(f"TrendStrategy ({symbol}): Invalid risk calculation for LONG signal")
                
                if signal_direction:
                    final_leverage = _calculate_trend_leverage(signal_strength_score, market_regime_info.volatility_level, leverage_tiers_list, default_bot_leverage)
                    tp_str = f"{take_profit_price:.5f}" if pd.notna(take_profit_price) else "N/A"
                    logger.info(f"TrendStrategy ({symbol}): LONG SIGNAL GENERATED! Strength: {signal_strength_score:.2f}, "
                               f"Entry: {entry_price_proposal:.5f}, SL: {stop_loss_price:.5f}, TP: {tp_str}, Leverage: {final_leverage}x")

    # SHORT Signal Logic - Trending DOWN market
    elif market_regime_info.trend_direction == "DOWN":
        required_values_for_short = [current_close, current_high, ema_fast_val, ema_medium_val, ema_slow_val, 
                                   rsi_val, macd_line_val, macd_signal_val, atr_val]
        if any(pd.isna(val) for val in required_values_for_short):
            logger.warning(f"TrendStrategy ({symbol}): Missing indicator values for SHORT signal")
            return None

        # EMA alignment check: Fast < Medium < Slow and price below medium EMA
        if (ema_fast_val < ema_medium_val) and (ema_medium_val < ema_slow_val) and (current_close < ema_medium_val):
            signal_strength_score += 0.4
            
            # MACD bearish confirmation
            if (macd_line_val < macd_signal_val):
                signal_strength_score += 0.3
                
            # RSI in bearish zone but not oversold
            if (rsi_val < rsi_bear_zone_max and rsi_val > rsi_oversold):
                signal_strength_score += 0.3
                
            # Volume confirmation
            if pd.notna(current_volume) and pd.notna(volume_sma_val) and current_volume > volume_sma_val:
                signal_strength_score += 0.1

            # Generate signal if strength meets threshold
            if signal_strength_score >= min_signal_strength:
                signal_direction = TradeDirection.SHORT
                entry_price_proposal = current_close
                stop_loss_price = current_high + (atr_multiplier_sl * atr_val)
                risk_per_unit = stop_loss_price - entry_price_proposal if pd.notna(entry_price_proposal) and pd.notna(stop_loss_price) else 0.0
                
                if risk_per_unit > 1e-9:
                    take_profit_price = entry_price_proposal - (tp_rr_ratio * risk_per_unit)
                else:
                    take_profit_price = None
                    signal_direction = None
                    logger.warning(f"TrendStrategy ({symbol}): Invalid risk calculation for SHORT signal")
                
                if signal_direction:
                    final_leverage = _calculate_trend_leverage(signal_strength_score, market_regime_info.volatility_level, leverage_tiers_list, default_bot_leverage)
                    tp_str = f"{take_profit_price:.5f}" if pd.notna(take_profit_price) else "N/A"
                    logger.info(f"TrendStrategy ({symbol}): SHORT SIGNAL GENERATED! Strength: {signal_strength_score:.2f}, "
                               f"Entry: {entry_price_proposal:.5f}, SL: {stop_loss_price:.5f}, TP: {tp_str}, Leverage: {final_leverage}x")

    # Return trading signal if all conditions are met
    if signal_direction and pd.notna(stop_loss_price) and pd.notna(take_profit_price):
        return TradingSignal(
            symbol=symbol,
            direction=signal_direction,
            entry_price=float(entry_price_proposal),
            stop_loss=float(stop_loss_price),
            take_profit=float(take_profit_price),
            suggested_leverage=final_leverage,
            signal_strength=round(signal_strength_score, 2),
            strategy_name="TrendFollowingV1.2_Professional",
            trigger_price=float(current_close),
            timestamp=datetime.now(timezone.utc)
        )

    return None
