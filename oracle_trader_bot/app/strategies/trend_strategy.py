# app/strategies/trend_strategy.py
"""Enhanced trend-following strategy with EMA Cross variant."""
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging

from app.strategies.base_strategy import BaseStrategy
from app.schemas.trading_signal import TradingSignal, TradeDirection
from app.schemas.market_regime_schemas import MarketRegimeInfo
from app.core.config import settings

logger = logging.getLogger(__name__)


class TrendFollowingStrategy(BaseStrategy):
    """Enhanced trend-following strategy with multiple variants."""
    
    def __init__(self, config: Dict[str, Any] = None):
        default_config = {
            'ema_fast_period': settings.TREND_EMA_FAST_PERIOD,
            'ema_medium_period': settings.TREND_EMA_MEDIUM_PERIOD,
            'ema_slow_period': settings.TREND_EMA_SLOW_PERIOD,
            'rsi_period': settings.TREND_RSI_PERIOD,
            'rsi_overbought': settings.TREND_RSI_OVERBOUGHT,
            'rsi_oversold': settings.TREND_RSI_OVERSOLD,
            'rsi_bull_zone_min': settings.TREND_RSI_BULL_ZONE_MIN,
            'rsi_bear_zone_max': settings.TREND_RSI_BEAR_ZONE_MAX,
            'atr_period': settings.TREND_ATR_PERIOD_SL_TP,
            'atr_multiplier_sl': settings.TREND_ATR_MULTIPLIER_SL,
            'tp_rr_ratio': settings.TREND_TP_RR_RATIO,
            'min_signal_strength': settings.TREND_MIN_SIGNAL_STRENGTH,
            'leverage_tiers': settings.TREND_LEVERAGE_TIERS,
            'default_leverage': settings.BOT_DEFAULT_LEVERAGE,
            'variant': 'classic'  # Options: 'classic', 'ema_cross', 'momentum_breakout'
        }
        
        if config:
            default_config.update(config)
        
        super().__init__("TrendFollowingV2", default_config)
    
    def generate_signal(
        self,
        symbol: str,
        df_with_indicators: pd.DataFrame,
        market_regime_info: MarketRegimeInfo,
        current_open_positions: List[str],
        **kwargs
    ) -> Optional[TradingSignal]:
        """Generate trend-following signal with enhanced logic."""
        
        # Check if we already have a position
        if symbol in current_open_positions:
            return None
        
        # Validate market conditions
        if not self.validate_market_conditions(market_regime_info, df_with_indicators):
            return None
        
        # Check data sufficiency
        if len(df_with_indicators) < self.get_minimum_data_points():
            return None
        
        latest_data = df_with_indicators.iloc[-1]
        
        # Select variant
        variant = self.config.get('variant', 'classic')
        
        if variant == 'classic':
            signal = self._generate_classic_trend_signal(symbol, df_with_indicators, market_regime_info, latest_data)
        elif variant == 'ema_cross':
            signal = self._generate_ema_cross_signal(symbol, df_with_indicators, market_regime_info, latest_data)
        elif variant == 'momentum_breakout':
            signal = self._generate_momentum_breakout_signal(symbol, df_with_indicators, market_regime_info, latest_data)
        else:
            logger.warning(f"TrendStrategy: Unknown variant '{variant}', using classic")
            signal = self._generate_classic_trend_signal(symbol, df_with_indicators, market_regime_info, latest_data)
        
        if signal and self.validate_signal(signal):
            self.record_signal_generation()
            return signal
        
        return None
    
    def _generate_classic_trend_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        regime_info: MarketRegimeInfo,
        latest_data: pd.Series
    ) -> Optional[TradingSignal]:
        """Classic trend-following signal generation."""
        
        # Get indicator values
        ema_fast = latest_data.get(f'EMA_{self.config["ema_fast_period"]}')
        ema_medium = latest_data.get(f'EMA_{self.config["ema_medium_period"]}')
        ema_slow = latest_data.get(f'EMA_{self.config["ema_slow_period"]}')
        rsi = latest_data.get(f'RSI_{self.config["rsi_period"]}')
        macd_line = latest_data.get(f'MACD_{settings.TREND_MACD_FAST}_{settings.TREND_MACD_SLOW}_{settings.TREND_MACD_SIGNAL}')
        macd_signal = latest_data.get(f'MACDs_{settings.TREND_MACD_FAST}_{settings.TREND_MACD_SLOW}_{settings.TREND_MACD_SIGNAL}')
        atr = latest_data.get(f'ATR_{self.config["atr_period"]}')
        
        current_close = latest_data.get('close')
        current_high = latest_data.get('high')
        current_low = latest_data.get('low')
        volume = latest_data.get('volume')
        volume_sma = latest_data.get('VOL_SMA_20')
        
        # Validate required values
        required_values = [ema_fast, ema_medium, ema_slow, rsi, macd_line, macd_signal, atr, current_close, current_high, current_low]
        if any(pd.isna(val) for val in required_values):
            return None
        
        signal_strength = 0.0
        signal_direction = None
        
        # Long signal conditions
        if regime_info.trend_direction == "UP":
            # EMA alignment
            if ema_fast > ema_medium > ema_slow and current_close > ema_medium:
                signal_strength += 0.4
                
                # MACD confirmation
                if macd_line > macd_signal:
                    signal_strength += 0.3
                
                # RSI in bull zone
                if self.config["rsi_bull_zone_min"] < rsi < self.config["rsi_overbought"]:
                    signal_strength += 0.3
                
                # Volume confirmation
                if not pd.isna(volume) and not pd.isna(volume_sma) and volume > volume_sma:
                    signal_strength += 0.1
                
                if signal_strength >= self.config["min_signal_strength"]:
                    signal_direction = TradeDirection.LONG
        
        # Short signal conditions
        elif regime_info.trend_direction == "DOWN":
            # EMA alignment
            if ema_fast < ema_medium < ema_slow and current_close < ema_medium:
                signal_strength += 0.4
                
                # MACD confirmation
                if macd_line < macd_signal:
                    signal_strength += 0.3
                
                # RSI in bear zone
                if self.config["rsi_oversold"] < rsi < self.config["rsi_bear_zone_max"]:
                    signal_strength += 0.3
                
                # Volume confirmation
                if not pd.isna(volume) and not pd.isna(volume_sma) and volume > volume_sma:
                    signal_strength += 0.1
                
                if signal_strength >= self.config["min_signal_strength"]:
                    signal_direction = TradeDirection.SHORT
        
        if not signal_direction:
            return None
        
        # Calculate entry, SL, and TP
        entry_price = current_close
        
        if signal_direction == TradeDirection.LONG:
            stop_loss = current_low - (self.config["atr_multiplier_sl"] * atr)
            risk_per_unit = entry_price - stop_loss
        else:  # SHORT
            stop_loss = current_high + (self.config["atr_multiplier_sl"] * atr)
            risk_per_unit = stop_loss - entry_price
        
        if risk_per_unit <= 0:
            return None
        
        take_profit = entry_price + (self.config["tp_rr_ratio"] * risk_per_unit) if signal_direction == TradeDirection.LONG else entry_price - (self.config["tp_rr_ratio"] * risk_per_unit)
        
        # Calculate leverage
        leverage = self._calculate_leverage(signal_strength, regime_info.volatility_level)
        
        return TradingSignal(
            symbol=symbol,
            direction=signal_direction,
            entry_price=float(entry_price),
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
            suggested_leverage=leverage,
            signal_strength=round(signal_strength, 2),
            strategy_name=f"{self.name}_Classic",
            trigger_price=float(current_close),
            timestamp=datetime.now(timezone.utc)
        )
    
    def _generate_ema_cross_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        regime_info: MarketRegimeInfo,
        latest_data: pd.Series
    ) -> Optional[TradingSignal]:
        """EMA crossover-based signal generation."""
        
        # Look for EMA crossovers in recent data
        if len(df) < 3:
            return None
        
        recent_data = df.tail(3)
        ema_fast_col = f'EMA_{self.config["ema_fast_period"]}'
        ema_slow_col = f'EMA_{self.config["ema_slow_period"]}'
        
        if ema_fast_col not in df.columns or ema_slow_col not in df.columns:
            return None
        
        # Check for crossover
        current_fast = recent_data[ema_fast_col].iloc[-1]
        current_slow = recent_data[ema_slow_col].iloc[-1]
        prev_fast = recent_data[ema_fast_col].iloc[-2]
        prev_slow = recent_data[ema_slow_col].iloc[-2]
        
        # Bullish crossover
        bullish_cross = (current_fast > current_slow) and (prev_fast <= prev_slow)
        # Bearish crossover
        bearish_cross = (current_fast < current_slow) and (prev_fast >= prev_slow)
        
        if not (bullish_cross or bearish_cross):
            return None
        
        # Additional confirmations
        rsi = latest_data.get(f'RSI_{self.config["rsi_period"]}')
        atr = latest_data.get(f'ATR_{self.config["atr_period"]}')
        current_close = latest_data.get('close')
        current_high = latest_data.get('high')
        current_low = latest_data.get('low')
        
        if any(pd.isna(val) for val in [rsi, atr, current_close, current_high, current_low]):
            return None
        
        signal_strength = 0.6  # Base strength for crossover
        signal_direction = None
        
        if bullish_cross and regime_info.trend_direction in ["UP", "SIDEWAYS"]:
            # Additional RSI confirmation
            if rsi > 30:  # Not oversold
                signal_strength += 0.2
            signal_direction = TradeDirection.LONG
            
        elif bearish_cross and regime_info.trend_direction in ["DOWN", "SIDEWAYS"]:
            # Additional RSI confirmation
            if rsi < 70:  # Not overbought
                signal_strength += 0.2
            signal_direction = TradeDirection.SHORT
        
        if not signal_direction or signal_strength < self.config["min_signal_strength"]:
            return None
        
        # Calculate prices
        entry_price = current_close
        
        if signal_direction == TradeDirection.LONG:
            stop_loss = current_low - (self.config["atr_multiplier_sl"] * atr)
            risk_per_unit = entry_price - stop_loss
        else:  # SHORT
            stop_loss = current_high + (self.config["atr_multiplier_sl"] * atr)
            risk_per_unit = stop_loss - entry_price
        
        if risk_per_unit <= 0:
            return None
        
        take_profit = entry_price + (self.config["tp_rr_ratio"] * risk_per_unit) if signal_direction == TradeDirection.LONG else entry_price - (self.config["tp_rr_ratio"] * risk_per_unit)
        
        leverage = self._calculate_leverage(signal_strength, regime_info.volatility_level)
        
        return TradingSignal(
            symbol=symbol,
            direction=signal_direction,
            entry_price=float(entry_price),
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
            suggested_leverage=leverage,
            signal_strength=round(signal_strength, 2),
            strategy_name=f"{self.name}_EMACross",
            trigger_price=float(current_close),
            timestamp=datetime.now(timezone.utc)
        )
    
    def _generate_momentum_breakout_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        regime_info: MarketRegimeInfo,
        latest_data: pd.Series
    ) -> Optional[TradingSignal]:
        """Momentum breakout signal generation."""
        
        # Look for price breakouts with momentum confirmation
        if len(df) < 20:
            return None
        
        recent_data = df.tail(20)
        current_close = latest_data.get('close')
        current_high = latest_data.get('high')
        current_low = latest_data.get('low')
        rsi = latest_data.get(f'RSI_{self.config["rsi_period"]}')
        atr = latest_data.get(f'ATR_{self.config["atr_period"]}')
        volume = latest_data.get('volume')
        volume_sma = latest_data.get('VOL_SMA_20')
        
        if any(pd.isna(val) for val in [current_close, current_high, current_low, rsi, atr]):
            return None
        
        # Calculate resistance and support levels
        resistance = recent_data['high'].max()
        support = recent_data['low'].min()
        
        signal_strength = 0.0
        signal_direction = None
        
        # Bullish breakout
        if current_close > resistance and rsi > 50:
            signal_strength += 0.5
            
            # Volume confirmation
            if not pd.isna(volume) and not pd.isna(volume_sma) and volume > volume_sma * 1.2:
                signal_strength += 0.3
            
            # Momentum confirmation
            if rsi > 60:
                signal_strength += 0.2
            
            signal_direction = TradeDirection.LONG
        
        # Bearish breakout
        elif current_close < support and rsi < 50:
            signal_strength += 0.5
            
            # Volume confirmation
            if not pd.isna(volume) and not pd.isna(volume_sma) and volume > volume_sma * 1.2:
                signal_strength += 0.3
            
            # Momentum confirmation
            if rsi < 40:
                signal_strength += 0.2
            
            signal_direction = TradeDirection.SHORT
        
        if not signal_direction or signal_strength < self.config["min_signal_strength"]:
            return None
        
        # Calculate prices
        entry_price = current_close
        
        if signal_direction == TradeDirection.LONG:
            stop_loss = support - (self.config["atr_multiplier_sl"] * atr)
            risk_per_unit = entry_price - stop_loss
        else:  # SHORT
            stop_loss = resistance + (self.config["atr_multiplier_sl"] * atr)
            risk_per_unit = stop_loss - entry_price
        
        if risk_per_unit <= 0:
            return None
        
        take_profit = entry_price + (self.config["tp_rr_ratio"] * risk_per_unit) if signal_direction == TradeDirection.LONG else entry_price - (self.config["tp_rr_ratio"] * risk_per_unit)
        
        leverage = self._calculate_leverage(signal_strength, regime_info.volatility_level)
        
        return TradingSignal(
            symbol=symbol,
            direction=signal_direction,
            entry_price=float(entry_price),
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
            suggested_leverage=leverage,
            signal_strength=round(signal_strength, 2),
            strategy_name=f"{self.name}_MomentumBreakout",
            trigger_price=float(current_close),
            timestamp=datetime.now(timezone.utc)
        )
    
    def _calculate_leverage(self, signal_strength: float, volatility_level: Optional[str]) -> int:
        """Calculate leverage based on signal strength and volatility."""
        base_leverage = self.config["default_leverage"]
        
        # Apply leverage tiers based on signal strength
        for threshold, leverage_value in self.config["leverage_tiers"]:
            if signal_strength >= threshold:
                base_leverage = leverage_value
                break
        
        # Reduce leverage for high volatility
        if volatility_level == "HIGH":
            base_leverage = max(1, base_leverage // 2)
        
        return base_leverage
    
    def validate_market_conditions(
        self,
        market_regime_info: MarketRegimeInfo,
        df_with_indicators: pd.DataFrame
    ) -> bool:
        """Validate if market conditions are suitable for trend following."""
        
        # Trend strategies work best in trending markets
        variant = self.config.get('variant', 'classic')
        
        if variant == 'classic':
            return market_regime_info.is_trending
        elif variant == 'ema_cross':
            # EMA cross can work in both trending and ranging markets
            return True
        elif variant == 'momentum_breakout':
            # Breakout strategy works better with some volatility
            return market_regime_info.volatility_level in ['NORMAL', 'HIGH']
        
        return True
    
    def get_required_indicators(self) -> List[str]:
        """Get required indicators for this strategy."""
        return [
            f'EMA_{self.config["ema_fast_period"]}',
            f'EMA_{self.config["ema_medium_period"]}',
            f'EMA_{self.config["ema_slow_period"]}',
            f'RSI_{self.config["rsi_period"]}',
            f'MACD_{settings.TREND_MACD_FAST}_{settings.TREND_MACD_SLOW}_{settings.TREND_MACD_SIGNAL}',
            f'MACDs_{settings.TREND_MACD_FAST}_{settings.TREND_MACD_SLOW}_{settings.TREND_MACD_SIGNAL}',
            f'ATR_{self.config["atr_period"]}',
            'VOL_SMA_20'
        ]
    
    def get_minimum_data_points(self) -> int:
        """Get minimum data points required."""
        return max(
            self.config["ema_slow_period"],
            self.config["rsi_period"],
            self.config["atr_period"],
            settings.TREND_MACD_SLOW + settings.TREND_MACD_SIGNAL,
            20  # For volume SMA
        )