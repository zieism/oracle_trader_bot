# backend/app/strategies/range_trading_strategy.py
"""
Range Trading Strategy

Professional implementation of mean-reversion trading strategy using Bollinger Bands
and RSI oversold/overbought conditions. Designed for ranging/sideways market conditions.
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

def _calculate_range_leverage(
    signal_strength: float, 
    volatility_level: Optional[str],
    leverage_tiers: List[Tuple[float, int]], 
    default_bot_leverage: int 
) -> int:
    """
    Calculate leverage for range trading strategy.
    
    Range trading typically uses lower leverage than trend following due to
    more frequent trades and mean-reversion nature.
    
    Args:
        signal_strength: Calculated signal strength (0.0-1.0+)
        volatility_level: Market volatility assessment ("LOW", "MEDIUM", "HIGH")
        leverage_tiers: List of (min_strength, leverage) tuples
        default_bot_leverage: Default bot leverage setting
        
    Returns:
        Calculated leverage value (conservative for range trading)
    """
    # Start with conservative base leverage for range trading
    base_leverage = default_bot_leverage // 2 or 1 
    
    # Find applicable leverage tier based on signal strength
    applicable_leverages = [lev_val for strength_thresh, lev_val in leverage_tiers if signal_strength >= strength_thresh]
    if applicable_leverages:
        base_leverage = max(applicable_leverages)
    elif leverage_tiers: 
        base_leverage = 1 
    
    # Further reduce leverage in high volatility environments
    if volatility_level == "HIGH":
        adjusted_leverage = max(1, base_leverage // 2)
        logger.info(f"RangeStrategy: Leverage adjusted for HIGH volatility: base={base_leverage} -> adjusted={adjusted_leverage}")
        return adjusted_leverage
    
    return base_leverage

def generate_range_signal(
    symbol: str,
    df_with_indicators: pd.DataFrame, 
    market_regime_info: MarketRegimeInfo, 
    current_open_positions_symbols: List[str],
    rsi_period: int,
    rsi_overbought_entry: int,
    rsi_oversold_entry: int,
    bbands_period: int,
    bbands_std_dev: float,
    atr_period_sl_tp: int,
    atr_multiplier_sl: float,
    tp_rr_ratio: float,
    min_signal_strength: float,
    leverage_tiers_list: List[Tuple[float, int]],
    default_bot_leverage: int
) -> Optional[TradingSignal]:
    """
    Generate range trading signal based on mean-reversion strategy.
    
    Strategy Logic:
    - LONG signals when price touches lower Bollinger Band with RSI oversold
    - SHORT signals when price touches upper Bollinger Band with RSI overbought
    - Target middle Bollinger Band for take profits
    - Uses ATR-based stop losses
    
    Args:
        symbol: Trading symbol to analyze
        df_with_indicators: DataFrame with OHLCV data and calculated indicators
        market_regime_info: Current market regime analysis
        current_open_positions_symbols: List of symbols with open positions
        rsi_period: RSI calculation period
        rsi_overbought_entry: RSI overbought threshold for SHORT signals
        rsi_oversold_entry: RSI oversold threshold for LONG signals
        bbands_period: Bollinger Bands calculation period
        bbands_std_dev: Bollinger Bands standard deviation multiplier
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
    min_lookback = max(bbands_period, rsi_period, atr_period_sl_tp)
    if df_with_indicators is None or df_with_indicators.empty or len(df_with_indicators) < min_lookback:
        logger.warning(f"RangeStrategy ({symbol}): Not enough data (need {min_lookback}). Has: {len(df_with_indicators) if df_with_indicators is not None else 0}")
        return None

    latest_data = df_with_indicators.iloc[-1]
    
    # Skip if position already open for this symbol
    if symbol in current_open_positions_symbols:
        logger.debug(f"RangeStrategy ({symbol}): Position already open, skipping")
        return None

    # Initialize signal variables
    signal_direction: Optional[TradeDirection] = None
    entry_price_proposal: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    final_leverage: int = 1 
    signal_strength_score: float = 0.0

    # Define indicator column names
    rsi_col = f'RSI_{rsi_period}'
    std_dev_str = str(bbands_std_dev).replace('.', '_')
    bb_lower_col = f'BBL_{bbands_period}_{std_dev_str}'
    bb_middle_col = f'BBM_{bbands_period}_{std_dev_str}'
    bb_upper_col = f'BBU_{bbands_period}_{std_dev_str}'
    atr_col = f'ATR_{atr_period_sl_tp}'

    # Extract current market data
    current_close = latest_data.get('close')
    current_high = latest_data.get('high')
    current_low = latest_data.get('low')
    rsi_val = latest_data.get(rsi_col) 
    bb_lower_val = latest_data.get(bb_lower_col)
    bb_middle_val = latest_data.get(bb_middle_col) 
    bb_upper_val = latest_data.get(bb_upper_col)
    atr_val = latest_data.get(atr_col)

    # Log current data for debugging
    logger.debug(f"RangeStrategy ({symbol}) Latest Data: Close={current_close}, Low={current_low}, High={current_high}, "
                 f"RSI({rsi_col})={rsi_val}, BBL={bb_lower_val}, BBM={bb_middle_val}, BBU={bb_upper_val}, ATR={atr_val}")

    # Validate required indicator values
    required_values = [current_close, current_high, current_low, rsi_val, bb_lower_val, bb_middle_val, bb_upper_val, atr_val]
    if any(pd.isna(val) for val in required_values):
        nan_fields = [name for name, val in zip(['close', 'high', 'low', rsi_col, bb_lower_col, bb_middle_col, bb_upper_col, atr_col], required_values) if pd.isna(val)]
        logger.warning(f"RangeStrategy ({symbol}): Missing critical indicator values. NaN fields: {nan_fields}")
        return None

    # LONG Signal Logic - Price near lower BB with RSI oversold
    price_touched_lower_bb = (current_low <= bb_lower_val) 
    rsi_is_oversold = (rsi_val < rsi_oversold_entry)
    
    logger.debug(f"RangeStrategy ({symbol}) LONG Check: PriceAtBBL={price_touched_lower_bb} "
                 f"(Low:{current_low:.5f} vs BBL:{bb_lower_val:.5f}), RSI_Oversold={rsi_is_oversold} "
                 f"(RSI:{rsi_val:.2f} vs Thresh:{rsi_oversold_entry})")

    if price_touched_lower_bb and rsi_is_oversold:
        logger.info(f"RangeStrategy ({symbol}): LONG conditions met - price at lower BB with RSI oversold")
        
        # Calculate signal strength
        signal_strength_score = 0.0
        if price_touched_lower_bb: 
            signal_strength_score += 0.5
        if rsi_is_oversold: 
            signal_strength_score += 0.3       
        if rsi_val < (rsi_oversold_entry - 5): 
            signal_strength_score += 0.2  # Extra strength for deeply oversold
        
        logger.debug(f"RangeStrategy ({symbol}) LONG Strength: {signal_strength_score:.2f} vs MinRequired: {min_signal_strength}")
        
        if signal_strength_score >= min_signal_strength:
            signal_direction = TradeDirection.LONG
            entry_price_proposal = current_close 
            stop_loss_price = current_low - (atr_multiplier_sl * atr_val)
            
            # Validate stop loss placement
            if pd.isna(stop_loss_price) or stop_loss_price >= entry_price_proposal:
                stop_loss_price = entry_price_proposal * (1 - ( (atr_multiplier_sl * atr_val / entry_price_proposal) if entry_price_proposal > 0 and pd.notna(atr_val) and (atr_multiplier_sl * atr_val / entry_price_proposal) < 0.05 else 0.005) ) 
                logger.info(f"RangeStrategy ({symbol}): LONG - Adjusted SL to {stop_loss_price:.5f}")

            # Calculate take profit
            risk_per_unit = entry_price_proposal - stop_loss_price if pd.notna(entry_price_proposal) and pd.notna(stop_loss_price) else 0.0
            if risk_per_unit > 1e-9: 
                take_profit_price = entry_price_proposal + (tp_rr_ratio * risk_per_unit)
                # Cap take profit at middle Bollinger Band for range trading
                if pd.notna(bb_middle_val) and take_profit_price > bb_middle_val: 
                    take_profit_price = bb_middle_val
                    logger.info(f"RangeStrategy ({symbol}): LONG - TP capped at middle BB: {take_profit_price:.5f}")
            else:
                take_profit_price = None
                signal_direction = None 
                logger.warning(f"RangeStrategy ({symbol}): LONG - Invalid risk calculation ({risk_per_unit:.5f})")
            
            if signal_direction:
                final_leverage = _calculate_range_leverage(signal_strength_score, market_regime_info.volatility_level, leverage_tiers_list, default_bot_leverage)
                logger.info(f"RangeStrategy ({symbol}): LONG SIGNAL GENERATED! Strength: {signal_strength_score:.2f}, "
                           f"Entry: {entry_price_proposal:.5f}, SL: {stop_loss_price:.5f}, TP: {take_profit_price:.5f}, Leverage: {final_leverage}x")
        else:
            logger.info(f"RangeStrategy ({symbol}): LONG conditions met but strength {signal_strength_score:.2f} < min {min_signal_strength}")

    # SHORT Signal Logic - Price near upper BB with RSI overbought (only if no LONG signal)
    if not signal_direction: 
        price_touched_upper_bb = (current_high >= bb_upper_val)
        rsi_is_overbought = (rsi_val > rsi_overbought_entry)
        
        logger.debug(f"RangeStrategy ({symbol}) SHORT Check: PriceAtBBU={price_touched_upper_bb} "
                     f"(High:{current_high:.5f} vs BBU:{bb_upper_val:.5f}), RSI_Overbought={rsi_is_overbought} "
                     f"(RSI:{rsi_val:.2f} vs Thresh:{rsi_overbought_entry})")

        if price_touched_upper_bb and rsi_is_overbought:
            logger.info(f"RangeStrategy ({symbol}): SHORT conditions met - price at upper BB with RSI overbought")
            
            # Calculate signal strength
            signal_strength_score = 0.0 
            if price_touched_upper_bb: 
                signal_strength_score += 0.5
            if rsi_is_overbought: 
                signal_strength_score += 0.3
            if rsi_val > (rsi_overbought_entry + 5): 
                signal_strength_score += 0.2  # Extra strength for deeply overbought

            logger.debug(f"RangeStrategy ({symbol}) SHORT Strength: {signal_strength_score:.2f} vs MinRequired: {min_signal_strength}")
            
            if signal_strength_score >= min_signal_strength:
                signal_direction = TradeDirection.SHORT
                entry_price_proposal = current_close
                stop_loss_price = current_high + (atr_multiplier_sl * atr_val)

                # Validate stop loss placement
                if pd.isna(stop_loss_price) or stop_loss_price <= entry_price_proposal:
                    stop_loss_price = entry_price_proposal * (1 + ( (atr_multiplier_sl * atr_val / entry_price_proposal) if entry_price_proposal > 0 and pd.notna(atr_val) and (atr_multiplier_sl * atr_val / entry_price_proposal) < 0.05 else 0.005) )
                    logger.info(f"RangeStrategy ({symbol}): SHORT - Adjusted SL to {stop_loss_price:.5f}")

                # Calculate take profit
                risk_per_unit = stop_loss_price - entry_price_proposal if pd.notna(entry_price_proposal) and pd.notna(stop_loss_price) else 0.0
                if risk_per_unit > 1e-9:
                    take_profit_price = entry_price_proposal - (tp_rr_ratio * risk_per_unit)
                    # Cap take profit at middle Bollinger Band for range trading
                    if pd.notna(bb_middle_val) and take_profit_price < bb_middle_val: 
                        take_profit_price = bb_middle_val
                        logger.info(f"RangeStrategy ({symbol}): SHORT - TP capped at middle BB: {take_profit_price:.5f}")
                else:
                    take_profit_price = None
                    signal_direction = None
                    logger.warning(f"RangeStrategy ({symbol}): SHORT - Invalid risk calculation ({risk_per_unit:.5f})")
                
                if signal_direction:
                    final_leverage = _calculate_range_leverage(signal_strength_score, market_regime_info.volatility_level, leverage_tiers_list, default_bot_leverage)
                    logger.info(f"RangeStrategy ({symbol}): SHORT SIGNAL GENERATED! Strength: {signal_strength_score:.2f}, "
                               f"Entry: {entry_price_proposal:.5f}, SL: {stop_loss_price:.5f}, TP: {take_profit_price:.5f}, Leverage: {final_leverage}x")
            else:
                logger.info(f"RangeStrategy ({symbol}): SHORT conditions met but strength {signal_strength_score:.2f} < min {min_signal_strength}")

    # Return trading signal if all conditions are met
    if signal_direction and pd.notna(stop_loss_price) and pd.notna(take_profit_price):
        entry_p = float(entry_price_proposal) if pd.notna(entry_price_proposal) else None
        trigger_p = float(current_close) if pd.notna(current_close) else None
        tp_p_final = float(take_profit_price) 
        sl_p_final = float(stop_loss_price)

        if tp_p_final is None or sl_p_final is None: 
            logger.warning(f"RangeStrategy ({symbol}): Final validation failed - SL or TP is None")
            return None

        return TradingSignal(
            symbol=symbol,
            direction=signal_direction,
            entry_price=entry_p,
            stop_loss=sl_p_final,
            take_profit=tp_p_final,
            suggested_leverage=final_leverage,
            signal_strength=round(signal_strength_score, 2),
            strategy_name="RangeTradingV1.1_Professional", 
            trigger_price=trigger_p,
            timestamp=datetime.now(timezone.utc)
        )
    elif signal_direction: 
        logger.warning(f"RangeStrategy ({symbol}): Signal direction set to {signal_direction.value} but SL/TP validation failed")

    return None
