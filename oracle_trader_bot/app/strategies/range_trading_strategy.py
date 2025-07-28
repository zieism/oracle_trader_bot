# app/strategies/range_trading_strategy.py
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any, Tuple 
from datetime import datetime, timezone
import logging 

from app.schemas.trading_signal import TradingSignal, TradeDirection
from app.schemas.market_regime_schemas import MarketRegimeInfo 
from app.core.config import settings 

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Ensure debug messages from this module are processed

def _calculate_range_leverage(
    signal_strength: float, 
    volatility_level: Optional[str],
    leverage_tiers: List[Tuple[float, int]], 
    default_bot_leverage: int 
) -> int:
    base_leverage = default_bot_leverage // 2 or 1 
    
    applicable_leverages = [lev_val for strength_thresh, lev_val in leverage_tiers if signal_strength >= strength_thresh]
    if applicable_leverages:
        base_leverage = max(applicable_leverages)
    elif leverage_tiers: 
        base_leverage = 1 
    
    if volatility_level == "HIGH":
        adjusted_leverage = max(1, base_leverage // 2)
        logger.debug(f"RangeStrategy: Leverage adjusted for HIGH volatility: base={base_leverage} -> adjusted={adjusted_leverage}")
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
    min_lookback = max(bbands_period, rsi_period, atr_period_sl_tp)
    if df_with_indicators is None or df_with_indicators.empty or len(df_with_indicators) < min_lookback:
        logger.warning(f"RangeStrategy ({symbol}): Not enough data (need {min_lookback}). Has: {len(df_with_indicators) if df_with_indicators is not None else 0}")
        return None

    latest_data = df_with_indicators.iloc[-1]
    
    if symbol in current_open_positions_symbols:
        return None

    signal_direction: Optional[TradeDirection] = None
    entry_price_proposal: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    final_leverage: int = 1 
    signal_strength_score: float = 0.0

    rsi_col = f'RSI_{rsi_period}'
    std_dev_str = str(bbands_std_dev).replace('.', '_')
    bb_lower_col = f'BBL_{bbands_period}_{std_dev_str}'
    bb_middle_col = f'BBM_{bbands_period}_{std_dev_str}'
    bb_upper_col = f'BBU_{bbands_period}_{std_dev_str}'
    atr_col = f'ATR_{atr_period_sl_tp}'

    current_close = latest_data.get('close')
    current_high = latest_data.get('high')
    current_low = latest_data.get('low')
    rsi_val = latest_data.get(rsi_col) 
    bb_lower_val = latest_data.get(bb_lower_col)
    bb_middle_val = latest_data.get(bb_middle_col) 
    bb_upper_val = latest_data.get(bb_upper_col)
    atr_val = latest_data.get(atr_col)

    # Moved this log to before the NaN check
    logger.debug(f"RangeStrategy ({symbol}) Latest Data Check: Close={current_close}, Low={current_low}, High={current_high}, "
                 f"RSI({rsi_col})={rsi_val}, BBL({bb_lower_col})={bb_lower_val}, "
                 f"BBM({bb_middle_col})={bb_middle_val}, BBU({bb_upper_col})={bb_upper_val}, ATR({atr_col})={atr_val}")

    required_values = [current_close, current_high, current_low, rsi_val, bb_lower_val, bb_middle_val, bb_upper_val, atr_val]
    if any(pd.isna(val) for val in required_values):
        # Log which specific values are NaN
        nan_fields = [name for name, val in zip(['close', 'high', 'low', rsi_col, bb_lower_col, bb_middle_col, bb_upper_col, atr_col], required_values) if pd.isna(val)]
        logger.warning(f"RangeStrategy ({symbol}): Missing critical indicator values from latest_data. NaN fields: {nan_fields}. Skipping signal generation.")
        return None

    # --- Check for LONG Reversal from Lower Bollinger Band ---
    price_touched_lower_bb = (current_low <= bb_lower_val) 
    rsi_is_oversold = (rsi_val < rsi_oversold_entry)
    
    logger.debug(f"RangeStrategy ({symbol}) LONG Condition Check: PriceNearBBL={price_touched_lower_bb} (Low:{current_low:.5f} vs BBL:{bb_lower_val:.5f}). RSI_Oversold={rsi_is_oversold} (RSI:{rsi_val:.2f} vs Thresh:{rsi_oversold_entry})")

    if price_touched_lower_bb and rsi_is_oversold:
        logger.info(f"RangeStrategy ({symbol}): Potential LONG conditions met based on BB and RSI.")
        signal_strength_score = 0.0
        if price_touched_lower_bb: signal_strength_score += 0.5
        if rsi_is_oversold: signal_strength_score += 0.3       
        if rsi_val < (rsi_oversold_entry - 5) : signal_strength_score += 0.2 
        
        logger.debug(f"RangeStrategy ({symbol}) LONG Strength Score: {signal_strength_score:.2f} vs MinRequired: {min_signal_strength}")
        if signal_strength_score >= min_signal_strength:
            signal_direction = TradeDirection.LONG
            entry_price_proposal = current_close 
            stop_loss_price = current_low - (atr_multiplier_sl * atr_val)
            
            if pd.isna(stop_loss_price) or stop_loss_price >= entry_price_proposal :
                stop_loss_price = entry_price_proposal * (1 - ( (atr_multiplier_sl * atr_val / entry_price_proposal) if entry_price_proposal > 0 and pd.notna(atr_val) and (atr_multiplier_sl * atr_val / entry_price_proposal) < 0.05 else 0.005) ) 
                logger.info(f"RangeStrategy ({symbol}): LONG - Adjusted SL. New SL: {stop_loss_price:.5f}")

            risk_per_unit = entry_price_proposal - stop_loss_price if pd.notna(entry_price_proposal) and pd.notna(stop_loss_price) else 0.0
            if risk_per_unit > 1e-9: 
                take_profit_price = entry_price_proposal + (tp_rr_ratio * risk_per_unit)
                if pd.notna(bb_middle_val) and take_profit_price > bb_middle_val: 
                    take_profit_price = bb_middle_val
                    logger.info(f"RangeStrategy ({symbol}): LONG - TP adjusted to Middle Bollinger Band: {take_profit_price:.5f}")
            else:
                take_profit_price = None; signal_direction = None 
                logger.warning(f"RangeStrategy ({symbol}): LONG - Invalid risk_per_unit ({risk_per_unit:.5f}). Signal invalidated.")
            
            if signal_direction:
                final_leverage = _calculate_range_leverage(signal_strength_score, market_regime_info.volatility_level, leverage_tiers_list, default_bot_leverage)
                logger.info(f"RangeStrategy ({symbol}): LONG SIGNAL GENERATED! Strength: {signal_strength_score:.2f}, Entry: {entry_price_proposal:.5f}, SL: {stop_loss_price:.5f}, TP: {take_profit_price:.5f if pd.notna(take_profit_price) else 'N/A'}, Leverage: {final_leverage}x")
        else:
            logger.info(f"RangeStrategy ({symbol}): LONG conditions met criteria but strength score {signal_strength_score:.2f} < min {min_signal_strength}.")

    # --- Check for SHORT Reversal from Upper Bollinger Band (only if no LONG signal) ---
    if not signal_direction: 
        price_touched_upper_bb = (current_high >= bb_upper_val)
        rsi_is_overbought = (rsi_val > rsi_overbought_entry)
        
        logger.debug(f"RangeStrategy ({symbol}) SHORT Condition Check: PriceNearBBU={price_touched_upper_bb} (High:{current_high:.5f} vs BBU:{bb_upper_val:.5f}). RSI_Overbought={rsi_is_overbought} (RSI:{rsi_val:.2f} vs Thresh:{rsi_overbought_entry})")

        if price_touched_upper_bb and rsi_is_overbought:
            logger.info(f"RangeStrategy ({symbol}): Potential SHORT conditions met based on BB and RSI.")
            signal_strength_score = 0.0 
            if price_touched_upper_bb: signal_strength_score += 0.5
            if rsi_is_overbought: signal_strength_score += 0.3
            if rsi_val > (rsi_overbought_entry + 5): signal_strength_score += 0.2 

            logger.debug(f"RangeStrategy ({symbol}) SHORT Strength Score: {signal_strength_score:.2f} vs MinRequired: {min_signal_strength}")
            if signal_strength_score >= min_signal_strength:
                signal_direction = TradeDirection.SHORT
                entry_price_proposal = current_close
                stop_loss_price = current_high + (atr_multiplier_sl * atr_val)

                if pd.isna(stop_loss_price) or stop_loss_price <= entry_price_proposal:
                    stop_loss_price = entry_price_proposal * (1 + ( (atr_multiplier_sl * atr_val / entry_price_proposal) if entry_price_proposal > 0 and pd.notna(atr_val) and (atr_multiplier_sl * atr_val / entry_price_proposal) < 0.05 else 0.005) )
                    logger.info(f"RangeStrategy ({symbol}): SHORT - Adjusted SL. New SL: {stop_loss_price:.5f}")

                risk_per_unit = stop_loss_price - entry_price_proposal if pd.notna(entry_price_proposal) and pd.notna(stop_loss_price) else 0.0
                if risk_per_unit > 1e-9:
                    take_profit_price = entry_price_proposal - (tp_rr_ratio * risk_per_unit)
                    if pd.notna(bb_middle_val) and take_profit_price < bb_middle_val: 
                        take_profit_price = bb_middle_val
                        logger.info(f"RangeStrategy ({symbol}): SHORT - TP adjusted to Middle Bollinger Band: {take_profit_price:.5f}")
                else:
                    take_profit_price = None; signal_direction = None
                    logger.warning(f"RangeStrategy ({symbol}): SHORT - Invalid risk_per_unit ({risk_per_unit:.5f}). Signal invalidated.")
                
                if signal_direction:
                    final_leverage = _calculate_range_leverage(signal_strength_score, market_regime_info.volatility_level, leverage_tiers_list, default_bot_leverage)
                    logger.info(f"RangeStrategy ({symbol}): SHORT SIGNAL GENERATED! Strength: {signal_strength_score:.2f}, Entry: {entry_price_proposal:.5f}, SL: {stop_loss_price:.5f}, TP: {take_profit_price:.5f if pd.notna(take_profit_price) else 'N/A'}, Leverage: {final_leverage}x")
            else:
                logger.info(f"RangeStrategy ({symbol}): SHORT conditions met criteria but strength score {signal_strength_score:.2f} < min {min_signal_strength}.")

    if signal_direction and pd.notna(stop_loss_price) and pd.notna(take_profit_price):
        entry_p = float(entry_price_proposal) if pd.notna(entry_price_proposal) else None
        trigger_p = float(current_close) if pd.notna(current_close) else None
        tp_p_final = float(take_profit_price) 
        sl_p_final = float(stop_loss_price)

        if tp_p_final is None or sl_p_final is None: 
            logger.warning(f"RangeStrategy ({symbol}): Final check, SL or TP is None after calculation. Invalidating signal.")
            return None

        return TradingSignal(
            symbol=symbol,
            direction=signal_direction,
            entry_price=entry_p,
            stop_loss=sl_p_final,
            take_profit=tp_p_final,
            suggested_leverage=final_leverage,
            signal_strength=round(signal_strength_score, 2),
            strategy_name="RangeTradingV1.1_Configurable", 
            trigger_price=trigger_p,
            timestamp=datetime.now(timezone.utc)
        )
    elif signal_direction: 
        logger.warning(f"RangeStrategy ({symbol}): Signal direction was set to {signal_direction.value} but SL/TP was invalid. No signal generated.")

    return None
