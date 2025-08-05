# app/strategies/range_strategy.py
"""Enhanced range trading strategy."""
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


class RangeTradingStrategy(BaseStrategy):
    """Enhanced range trading strategy for sideways markets."""
    
    def __init__(self, config: Dict[str, Any] = None):
        default_config = {
            'rsi_period': settings.RANGE_RSI_PERIOD,
            'rsi_overbought': settings.RANGE_RSI_OVERBOUGHT,
            'rsi_oversold': settings.RANGE_RSI_OVERSOLD,
            'bbands_period': settings.RANGE_BBANDS_PERIOD,
            'bbands_std_dev': settings.RANGE_BBANDS_STD_DEV,
            'atr_period': settings.RANGE_ATR_PERIOD_SL_TP,
            'atr_multiplier_sl': settings.RANGE_ATR_MULTIPLIER_SL,
            'tp_rr_ratio': settings.RANGE_TP_RR_RATIO,
            'min_signal_strength': settings.RANGE_MIN_SIGNAL_STRENGTH,
            'leverage_tiers': settings.RANGE_LEVERAGE_TIERS,
            'default_leverage': max(1, settings.BOT_DEFAULT_LEVERAGE // 2),
            'variant': 'classic',  # Options: 'classic', 'mean_reversion', 'support_resistance'
            'oversold_extreme': 20,  # Extreme oversold level
            'overbought_extreme': 80,  # Extreme overbought level
            'volume_multiplier': 1.2  # Volume confirmation multiplier
        }
        
        if config:
            default_config.update(config)
        
        super().__init__("RangeTradingV2", default_config)
    
    def generate_signal(
        self,
        symbol: str,
        df_with_indicators: pd.DataFrame,
        market_regime_info: MarketRegimeInfo,
        current_open_positions: List[str],
        **kwargs
    ) -> Optional[TradingSignal]:
        """Generate range trading signal."""
        
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
            signal = self._generate_classic_range_signal(symbol, df_with_indicators, market_regime_info, latest_data)
        elif variant == 'mean_reversion':
            signal = self._generate_mean_reversion_signal(symbol, df_with_indicators, market_regime_info, latest_data)
        elif variant == 'support_resistance':
            signal = self._generate_support_resistance_signal(symbol, df_with_indicators, market_regime_info, latest_data)
        else:
            logger.warning(f"RangeStrategy: Unknown variant '{variant}', using classic")
            signal = self._generate_classic_range_signal(symbol, df_with_indicators, market_regime_info, latest_data)
        
        if signal and self.validate_signal(signal):
            self.record_signal_generation()
            return signal
        
        return None
    
    def _generate_classic_range_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        regime_info: MarketRegimeInfo,
        latest_data: pd.Series
    ) -> Optional[TradingSignal]:
        """Classic range trading signal using Bollinger Bands and RSI."""
        
        # Get indicator values
        rsi = latest_data.get(f'RSI_{self.config["rsi_period"]}')
        
        # Construct Bollinger Band column names
        std_dev_str = str(self.config["bbands_std_dev"]).replace('.', '_')
        bb_lower = latest_data.get(f'BBL_{self.config["bbands_period"]}_{std_dev_str}')
        bb_middle = latest_data.get(f'BBM_{self.config["bbands_period"]}_{std_dev_str}')
        bb_upper = latest_data.get(f'BBU_{self.config["bbands_period"]}_{std_dev_str}')
        
        atr = latest_data.get(f'ATR_{self.config["atr_period"]}')
        current_close = latest_data.get('close')
        current_high = latest_data.get('high')
        current_low = latest_data.get('low')
        volume = latest_data.get('volume')
        volume_sma = latest_data.get('VOL_SMA_20')
        
        # Validate required values
        required_values = [rsi, bb_lower, bb_middle, bb_upper, atr, current_close, current_high, current_low]
        if any(pd.isna(val) for val in required_values):
            logger.debug(f"RangeStrategy: Missing indicator values for {symbol}")
            return None
        
        signal_strength = 0.0
        signal_direction = None
        
        # Long signal: Price near lower BB and RSI oversold
        price_near_lower_bb = current_low <= bb_lower
        rsi_oversold = rsi < self.config["rsi_oversold"]
        
        if price_near_lower_bb and rsi_oversold:
            signal_strength += 0.5  # Base strength for BB touch
            signal_strength += 0.3  # RSI confirmation
            
            # Additional confirmation for extreme oversold
            if rsi < self.config["oversold_extreme"]:
                signal_strength += 0.2
            
            # Volume confirmation
            if not pd.isna(volume) and not pd.isna(volume_sma) and volume > volume_sma * self.config["volume_multiplier"]:
                signal_strength += 0.1
            
            if signal_strength >= self.config["min_signal_strength"]:
                signal_direction = TradeDirection.LONG
        
        # Short signal: Price near upper BB and RSI overbought
        if not signal_direction:
            price_near_upper_bb = current_high >= bb_upper
            rsi_overbought = rsi > self.config["rsi_overbought"]
            
            if price_near_upper_bb and rsi_overbought:
                signal_strength = 0.5  # Reset strength for short signal
                signal_strength += 0.3  # RSI confirmation
                
                # Additional confirmation for extreme overbought
                if rsi > self.config["overbought_extreme"]:
                    signal_strength += 0.2
                
                # Volume confirmation
                if not pd.isna(volume) and not pd.isna(volume_sma) and volume > volume_sma * self.config["volume_multiplier"]:
                    signal_strength += 0.1
                
                if signal_strength >= self.config["min_signal_strength"]:
                    signal_direction = TradeDirection.SHORT
        
        if not signal_direction:
            return None
        
        # Calculate entry, SL, and TP
        entry_price = current_close
        
        if signal_direction == TradeDirection.LONG:
            stop_loss = current_low - (self.config["atr_multiplier_sl"] * atr)
            if stop_loss >= entry_price:
                stop_loss = entry_price * (1 - 0.005)  # 0.5% fallback SL
            
            risk_per_unit = entry_price - stop_loss
            take_profit = entry_price + (self.config["tp_rr_ratio"] * risk_per_unit)
            
            # Cap TP at middle BB for mean reversion
            if not pd.isna(bb_middle) and take_profit > bb_middle:
                take_profit = bb_middle
        
        else:  # SHORT
            stop_loss = current_high + (self.config["atr_multiplier_sl"] * atr)
            if stop_loss <= entry_price:
                stop_loss = entry_price * (1 + 0.005)  # 0.5% fallback SL
            
            risk_per_unit = stop_loss - entry_price
            take_profit = entry_price - (self.config["tp_rr_ratio"] * risk_per_unit)
            
            # Cap TP at middle BB for mean reversion
            if not pd.isna(bb_middle) and take_profit < bb_middle:
                take_profit = bb_middle
        
        if risk_per_unit <= 0:
            return None
        
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
    
    def _generate_mean_reversion_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        regime_info: MarketRegimeInfo,
        latest_data: pd.Series
    ) -> Optional[TradingSignal]:
        """Mean reversion signal based on statistical deviations."""
        
        if len(df) < 50:  # Need enough data for statistical analysis
            return None
        
        # Calculate Z-score for mean reversion
        recent_prices = df['close'].tail(20)
        price_mean = recent_prices.mean()
        price_std = recent_prices.std()
        
        current_close = latest_data.get('close')
        rsi = latest_data.get(f'RSI_{self.config["rsi_period"]}')
        atr = latest_data.get(f'ATR_{self.config["atr_period"]}')
        
        if any(pd.isna(val) for val in [current_close, rsi, atr]) or price_std == 0:
            return None
        
        z_score = (current_close - price_mean) / price_std
        
        signal_strength = 0.0
        signal_direction = None
        
        # Long signal: Price significantly below mean and RSI oversold
        if z_score < -1.5 and rsi < self.config["rsi_oversold"]:
            signal_strength = min(1.0, abs(z_score) / 2.0)  # Strength based on Z-score
            
            # RSI confirmation
            if rsi < 30:
                signal_strength += 0.2
            
            signal_direction = TradeDirection.LONG
        
        # Short signal: Price significantly above mean and RSI overbought
        elif z_score > 1.5 and rsi > self.config["rsi_overbought"]:
            signal_strength = min(1.0, abs(z_score) / 2.0)  # Strength based on Z-score
            
            # RSI confirmation
            if rsi > 70:
                signal_strength += 0.2
            
            signal_direction = TradeDirection.SHORT
        
        if not signal_direction or signal_strength < self.config["min_signal_strength"]:
            return None
        
        # Calculate prices with mean reversion targets
        entry_price = current_close
        
        if signal_direction == TradeDirection.LONG:
            stop_loss = current_close - (2 * atr)  # Wider SL for mean reversion
            take_profit = price_mean  # Target mean price
        else:  # SHORT
            stop_loss = current_close + (2 * atr)  # Wider SL for mean reversion
            take_profit = price_mean  # Target mean price
        
        # Validate risk/reward
        risk_per_unit = abs(entry_price - stop_loss)
        reward_per_unit = abs(take_profit - entry_price)
        
        if risk_per_unit <= 0 or reward_per_unit / risk_per_unit < 0.5:  # Lower RR for mean reversion
            return None
        
        leverage = self._calculate_leverage(signal_strength, regime_info.volatility_level)
        
        return TradingSignal(
            symbol=symbol,
            direction=signal_direction,
            entry_price=float(entry_price),
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
            suggested_leverage=leverage,
            signal_strength=round(signal_strength, 2),
            strategy_name=f"{self.name}_MeanReversion",
            trigger_price=float(current_close),
            timestamp=datetime.now(timezone.utc)
        )
    
    def _generate_support_resistance_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        regime_info: MarketRegimeInfo,
        latest_data: pd.Series
    ) -> Optional[TradingSignal]:
        """Support/resistance level trading signal."""
        
        if len(df) < 50:
            return None
        
        # Identify support and resistance levels
        recent_data = df.tail(50)
        support_levels = self._find_support_levels(recent_data)
        resistance_levels = self._find_resistance_levels(recent_data)
        
        current_close = latest_data.get('close')
        current_high = latest_data.get('high')
        current_low = latest_data.get('low')
        rsi = latest_data.get(f'RSI_{self.config["rsi_period"]}')
        atr = latest_data.get(f'ATR_{self.config["atr_period"]}')
        
        if any(pd.isna(val) for val in [current_close, current_high, current_low, rsi, atr]):
            return None
        
        signal_strength = 0.0
        signal_direction = None
        
        # Check for bounces off support levels
        for support in support_levels:
            if abs(current_low - support) / support < 0.005:  # Within 0.5% of support
                if rsi < 50:  # Momentum confirmation
                    signal_strength = 0.6
                    
                    # Additional confirmations
                    if rsi < 40:
                        signal_strength += 0.2
                    
                    signal_direction = TradeDirection.LONG
                    stop_loss = support - (self.config["atr_multiplier_sl"] * atr)
                    
                    # Find next resistance for TP
                    next_resistance = min([r for r in resistance_levels if r > current_close], default=current_close * 1.03)
                    take_profit = next_resistance
                    break
        
        # Check for rejections at resistance levels
        if not signal_direction:
            for resistance in resistance_levels:
                if abs(current_high - resistance) / resistance < 0.005:  # Within 0.5% of resistance
                    if rsi > 50:  # Momentum confirmation
                        signal_strength = 0.6
                        
                        # Additional confirmations
                        if rsi > 60:
                            signal_strength += 0.2
                        
                        signal_direction = TradeDirection.SHORT
                        stop_loss = resistance + (self.config["atr_multiplier_sl"] * atr)
                        
                        # Find next support for TP
                        next_support = max([s for s in support_levels if s < current_close], default=current_close * 0.97)
                        take_profit = next_support
                        break
        
        if not signal_direction or signal_strength < self.config["min_signal_strength"]:
            return None
        
        # Validate risk/reward
        entry_price = current_close
        risk_per_unit = abs(entry_price - stop_loss)
        reward_per_unit = abs(take_profit - entry_price)
        
        if risk_per_unit <= 0 or reward_per_unit / risk_per_unit < 1.0:
            return None
        
        leverage = self._calculate_leverage(signal_strength, regime_info.volatility_level)
        
        return TradingSignal(
            symbol=symbol,
            direction=signal_direction,
            entry_price=float(entry_price),
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
            suggested_leverage=leverage,
            signal_strength=round(signal_strength, 2),
            strategy_name=f"{self.name}_SupportResistance",
            trigger_price=float(current_close),
            timestamp=datetime.now(timezone.utc)
        )
    
    def _find_support_levels(self, df: pd.DataFrame) -> List[float]:
        """Find key support levels."""
        lows = df['low'].values
        support_levels = []
        
        # Simple approach: find local minima
        for i in range(2, len(lows) - 2):
            if lows[i] == min(lows[i-2:i+3]):
                support_levels.append(lows[i])
        
        # Return unique levels sorted
        return sorted(list(set(support_levels)))
    
    def _find_resistance_levels(self, df: pd.DataFrame) -> List[float]:
        """Find key resistance levels."""
        highs = df['high'].values
        resistance_levels = []
        
        # Simple approach: find local maxima
        for i in range(2, len(highs) - 2):
            if highs[i] == max(highs[i-2:i+3]):
                resistance_levels.append(highs[i])
        
        # Return unique levels sorted
        return sorted(list(set(resistance_levels)))
    
    def _calculate_leverage(self, signal_strength: float, volatility_level: Optional[str]) -> int:
        """Calculate leverage based on signal strength and volatility."""
        base_leverage = self.config["default_leverage"]
        
        # Apply leverage tiers (more conservative for range trading)
        for threshold, leverage_value in self.config["leverage_tiers"]:
            if signal_strength >= threshold:
                base_leverage = min(leverage_value, self.config["default_leverage"])
                break
        
        # Further reduce leverage for high volatility
        if volatility_level == "HIGH":
            base_leverage = max(1, base_leverage // 2)
        
        return base_leverage
    
    def validate_market_conditions(
        self,
        market_regime_info: MarketRegimeInfo,
        df_with_indicators: pd.DataFrame
    ) -> bool:
        """Validate if market conditions are suitable for range trading."""
        
        # Range strategies work best in sideways/ranging markets
        variant = self.config.get('variant', 'classic')
        
        if variant == 'classic':
            # Classic range trading prefers sideways markets with low to normal volatility
            return (market_regime_info.trend_direction == "SIDEWAYS" and 
                    market_regime_info.volatility_level in ['LOW', 'NORMAL', None])
        elif variant == 'mean_reversion':
            # Mean reversion can work in various conditions but avoid strong trends
            return not market_regime_info.is_strongly_trending
        elif variant == 'support_resistance':
            # Support/resistance works in most conditions
            return True
        
        return True
    
    def get_required_indicators(self) -> List[str]:
        """Get required indicators for this strategy."""
        std_dev_str = str(self.config["bbands_std_dev"]).replace('.', '_')
        return [
            f'RSI_{self.config["rsi_period"]}',
            f'BBL_{self.config["bbands_period"]}_{std_dev_str}',
            f'BBM_{self.config["bbands_period"]}_{std_dev_str}',
            f'BBU_{self.config["bbands_period"]}_{std_dev_str}',
            f'ATR_{self.config["atr_period"]}',
            'VOL_SMA_20'
        ]
    
    def get_minimum_data_points(self) -> int:
        """Get minimum data points required."""
        return max(
            self.config["bbands_period"],
            self.config["rsi_period"],
            self.config["atr_period"],
            20,  # For volume SMA
            50   # For support/resistance variant
        )