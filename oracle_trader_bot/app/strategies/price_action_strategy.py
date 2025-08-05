# app/strategies/price_action_strategy.py
"""Price action strategy based on candlestick patterns and market structure."""
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
import logging

from app.strategies.base_strategy import BaseStrategy
from app.schemas.trading_signal import TradingSignal, TradeDirection
from app.schemas.market_regime_schemas import MarketRegimeInfo

logger = logging.getLogger(__name__)


class PriceActionStrategy(BaseStrategy):
    """Price action strategy focusing on candlestick patterns and market structure."""
    
    def __init__(self, config: Dict[str, Any] = None):
        default_config = {
            'min_body_ratio': 0.3,  # Minimum body to range ratio for valid patterns
            'min_wick_ratio': 0.4,  # Minimum wick ratio for pin bars/hammers
            'engulfing_min_body': 0.5,  # Minimum body size for engulfing patterns
            'doji_max_body': 0.1,  # Maximum body size for doji (as ratio of range)
            'atr_period': 14,
            'atr_multiplier_sl': 1.5,
            'tp_rr_ratio': 2.0,
            'min_signal_strength': 0.6,
            'default_leverage': 3,  # Conservative leverage for price action
            'confirmation_periods': 2,  # Periods to wait for confirmation
            'pattern_weights': {
                'hammer': 0.8,
                'shooting_star': 0.8,
                'engulfing_bullish': 0.9,
                'engulfing_bearish': 0.9,
                'pin_bar_bullish': 0.7,
                'pin_bar_bearish': 0.7,
                'doji': 0.5,
                'inside_bar': 0.4,
                'outside_bar': 0.6
            }
        }
        
        if config:
            default_config.update(config)
        
        super().__init__("PriceActionV1", default_config)
    
    def generate_signal(
        self,
        symbol: str,
        df_with_indicators: pd.DataFrame,
        market_regime_info: MarketRegimeInfo,
        current_open_positions: List[str],
        **kwargs
    ) -> Optional[TradingSignal]:
        """Generate price action signal based on candlestick patterns."""
        
        # Check if we already have a position
        if symbol in current_open_positions:
            return None
        
        # Check data sufficiency
        if len(df_with_indicators) < self.get_minimum_data_points():
            return None
        
        # Get recent candles for pattern analysis
        recent_candles = df_with_indicators.tail(5)
        latest_candle = recent_candles.iloc[-1]
        
        # Detect patterns
        patterns = self._detect_patterns(recent_candles)
        if not patterns:
            return None
        
        # Analyze market structure
        market_structure = self._analyze_market_structure(df_with_indicators.tail(20))
        
        # Generate signal based on patterns and structure
        signal = self._generate_pattern_signal(
            symbol, patterns, market_structure, latest_candle, market_regime_info
        )
        
        if signal and self.validate_signal(signal):
            self.record_signal_generation()
            return signal
        
        return None
    
    def _detect_patterns(self, candles: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect various candlestick patterns."""
        patterns = []
        
        if len(candles) < 2:
            return patterns
        
        current = candles.iloc[-1]
        previous = candles.iloc[-2] if len(candles) >= 2 else None
        
        # Single candle patterns
        hammer = self._detect_hammer(current)
        if hammer:
            patterns.append(hammer)
        
        shooting_star = self._detect_shooting_star(current)
        if shooting_star:
            patterns.append(shooting_star)
        
        doji = self._detect_doji(current)
        if doji:
            patterns.append(doji)
        
        pin_bar = self._detect_pin_bar(current)
        if pin_bar:
            patterns.append(pin_bar)
        
        # Multi-candle patterns
        if previous is not None:
            engulfing = self._detect_engulfing(previous, current)
            if engulfing:
                patterns.append(engulfing)
            
            inside_bar = self._detect_inside_bar(previous, current)
            if inside_bar:
                patterns.append(inside_bar)
            
            outside_bar = self._detect_outside_bar(previous, current)
            if outside_bar:
                patterns.append(outside_bar)
        
        return patterns
    
    def _detect_hammer(self, candle: pd.Series) -> Optional[Dict[str, Any]]:
        """Detect hammer candlestick pattern."""
        open_price = candle['open']
        high = candle['high']
        low = candle['low']
        close = candle['close']
        
        # Calculate components
        body = abs(close - open_price)
        total_range = high - low
        lower_wick = min(open_price, close) - low
        upper_wick = high - max(open_price, close)
        
        if total_range == 0:
            return None
        
        # Hammer criteria
        body_ratio = body / total_range
        lower_wick_ratio = lower_wick / total_range
        upper_wick_ratio = upper_wick / total_range
        
        if (lower_wick_ratio >= self.config['min_wick_ratio'] and
            upper_wick_ratio <= 0.1 and
            body_ratio <= 0.3):
            
            return {
                'pattern': 'hammer',
                'bullish': True,
                'strength': min(1.0, lower_wick_ratio + (0.3 - body_ratio)),
                'candle_index': -1
            }
        
        return None
    
    def _detect_shooting_star(self, candle: pd.Series) -> Optional[Dict[str, Any]]:
        """Detect shooting star candlestick pattern."""
        open_price = candle['open']
        high = candle['high']
        low = candle['low']
        close = candle['close']
        
        # Calculate components
        body = abs(close - open_price)
        total_range = high - low
        lower_wick = min(open_price, close) - low
        upper_wick = high - max(open_price, close)
        
        if total_range == 0:
            return None
        
        # Shooting star criteria
        body_ratio = body / total_range
        lower_wick_ratio = lower_wick / total_range
        upper_wick_ratio = upper_wick / total_range
        
        if (upper_wick_ratio >= self.config['min_wick_ratio'] and
            lower_wick_ratio <= 0.1 and
            body_ratio <= 0.3):
            
            return {
                'pattern': 'shooting_star',
                'bullish': False,
                'strength': min(1.0, upper_wick_ratio + (0.3 - body_ratio)),
                'candle_index': -1
            }
        
        return None
    
    def _detect_doji(self, candle: pd.Series) -> Optional[Dict[str, Any]]:
        """Detect doji candlestick pattern."""
        open_price = candle['open']
        high = candle['high']
        low = candle['low']
        close = candle['close']
        
        body = abs(close - open_price)
        total_range = high - low
        
        if total_range == 0:
            return None
        
        body_ratio = body / total_range
        
        if body_ratio <= self.config['doji_max_body']:
            return {
                'pattern': 'doji',
                'bullish': None,  # Neutral pattern
                'strength': 1.0 - body_ratio,
                'candle_index': -1
            }
        
        return None
    
    def _detect_pin_bar(self, candle: pd.Series) -> Optional[Dict[str, Any]]:
        """Detect pin bar pattern."""
        open_price = candle['open']
        high = candle['high']
        low = candle['low']
        close = candle['close']
        
        body = abs(close - open_price)
        total_range = high - low
        lower_wick = min(open_price, close) - low
        upper_wick = high - max(open_price, close)
        
        if total_range == 0:
            return None
        
        body_ratio = body / total_range
        lower_wick_ratio = lower_wick / total_range
        upper_wick_ratio = upper_wick / total_range
        
        # Bullish pin bar (long lower wick)
        if (lower_wick_ratio >= self.config['min_wick_ratio'] and
            body_ratio <= 0.5 and
            lower_wick > upper_wick * 2):
            
            return {
                'pattern': 'pin_bar_bullish',
                'bullish': True,
                'strength': min(1.0, lower_wick_ratio),
                'candle_index': -1
            }
        
        # Bearish pin bar (long upper wick)
        elif (upper_wick_ratio >= self.config['min_wick_ratio'] and
              body_ratio <= 0.5 and
              upper_wick > lower_wick * 2):
            
            return {
                'pattern': 'pin_bar_bearish',
                'bullish': False,
                'strength': min(1.0, upper_wick_ratio),
                'candle_index': -1
            }
        
        return None
    
    def _detect_engulfing(self, prev_candle: pd.Series, current_candle: pd.Series) -> Optional[Dict[str, Any]]:
        """Detect bullish/bearish engulfing patterns."""
        
        # Previous candle
        prev_open = prev_candle['open']
        prev_close = prev_candle['close']
        prev_body = abs(prev_close - prev_open)
        
        # Current candle
        curr_open = current_candle['open']
        curr_close = current_candle['close']
        curr_body = abs(curr_close - curr_open)
        curr_range = current_candle['high'] - current_candle['low']
        
        if curr_range == 0:
            return None
        
        body_ratio = curr_body / curr_range
        
        # Bullish engulfing
        if (prev_close < prev_open and  # Previous red candle
            curr_close > curr_open and  # Current green candle
            curr_close > prev_open and  # Current close above previous open
            curr_open < prev_close and  # Current open below previous close
            curr_body > prev_body and   # Current body larger
            body_ratio >= self.config['engulfing_min_body']):
            
            return {
                'pattern': 'engulfing_bullish',
                'bullish': True,
                'strength': min(1.0, body_ratio + (curr_body / prev_body - 1) * 0.2),
                'candle_index': -1
            }
        
        # Bearish engulfing
        elif (prev_close > prev_open and  # Previous green candle
              curr_close < curr_open and  # Current red candle
              curr_close < prev_open and  # Current close below previous open
              curr_open > prev_close and  # Current open above previous close
              curr_body > prev_body and   # Current body larger
              body_ratio >= self.config['engulfing_min_body']):
            
            return {
                'pattern': 'engulfing_bearish',
                'bullish': False,
                'strength': min(1.0, body_ratio + (curr_body / prev_body - 1) * 0.2),
                'candle_index': -1
            }
        
        return None
    
    def _detect_inside_bar(self, prev_candle: pd.Series, current_candle: pd.Series) -> Optional[Dict[str, Any]]:
        """Detect inside bar pattern."""
        if (current_candle['high'] <= prev_candle['high'] and
            current_candle['low'] >= prev_candle['low']):
            
            # Calculate compression ratio
            prev_range = prev_candle['high'] - prev_candle['low']
            curr_range = current_candle['high'] - current_candle['low']
            compression_ratio = curr_range / prev_range if prev_range > 0 else 0
            
            return {
                'pattern': 'inside_bar',
                'bullish': None,  # Direction depends on breakout
                'strength': 1.0 - compression_ratio,
                'candle_index': -1
            }
        
        return None
    
    def _detect_outside_bar(self, prev_candle: pd.Series, current_candle: pd.Series) -> Optional[Dict[str, Any]]:
        """Detect outside bar pattern."""
        if (current_candle['high'] > prev_candle['high'] and
            current_candle['low'] < prev_candle['low']):
            
            # Calculate expansion ratio
            prev_range = prev_candle['high'] - prev_candle['low']
            curr_range = current_candle['high'] - current_candle['low']
            expansion_ratio = curr_range / prev_range if prev_range > 0 else 1
            
            # Determine direction based on close
            bullish = current_candle['close'] > current_candle['open']
            
            return {
                'pattern': 'outside_bar',
                'bullish': bullish,
                'strength': min(1.0, expansion_ratio - 1),
                'candle_index': -1
            }
        
        return None
    
    def _analyze_market_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze market structure for context."""
        if len(df) < 10:
            return {'structure': 'insufficient_data'}
        
        highs = df['high'].values
        lows = df['low'].values
        
        # Find swing highs and lows
        swing_highs = []
        swing_lows = []
        
        for i in range(2, len(highs) - 2):
            if highs[i] == max(highs[i-2:i+3]):
                swing_highs.append((i, highs[i]))
            if lows[i] == min(lows[i-2:i+3]):
                swing_lows.append((i, lows[i]))
        
        # Analyze structure
        structure_type = self._classify_structure(swing_highs, swing_lows)
        
        # Find key levels
        recent_high = max(highs[-10:])
        recent_low = min(lows[-10:])
        
        return {
            'structure': structure_type,
            'recent_high': recent_high,
            'recent_low': recent_low,
            'swing_highs': [price for _, price in swing_highs[-3:]],
            'swing_lows': [price for _, price in swing_lows[-3:]]
        }
    
    def _classify_structure(self, swing_highs: List[Tuple], swing_lows: List[Tuple]) -> str:
        """Classify market structure as uptrend, downtrend, or ranging."""
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return 'insufficient_data'
        
        # Get recent swing points
        recent_highs = [price for _, price in swing_highs[-2:]]
        recent_lows = [price for _, price in swing_lows[-2:]]
        
        # Higher highs and higher lows = uptrend
        if len(recent_highs) == 2 and len(recent_lows) == 2:
            if recent_highs[1] > recent_highs[0] and recent_lows[1] > recent_lows[0]:
                return 'uptrend'
            elif recent_highs[1] < recent_highs[0] and recent_lows[1] < recent_lows[0]:
                return 'downtrend'
        
        return 'ranging'
    
    def _generate_pattern_signal(
        self,
        symbol: str,
        patterns: List[Dict[str, Any]],
        market_structure: Dict[str, Any],
        latest_candle: pd.Series,
        regime_info: MarketRegimeInfo
    ) -> Optional[TradingSignal]:
        """Generate signal based on detected patterns and market structure."""
        
        # Filter patterns by strength and market context
        valid_patterns = []
        for pattern in patterns:
            pattern_weight = self.config['pattern_weights'].get(pattern['pattern'], 0.5)
            adjusted_strength = pattern['strength'] * pattern_weight
            
            # Check if pattern aligns with market structure
            if self._pattern_aligns_with_structure(pattern, market_structure):
                adjusted_strength *= 1.2
            
            if adjusted_strength >= 0.5:  # Minimum threshold
                pattern['adjusted_strength'] = adjusted_strength
                valid_patterns.append(pattern)
        
        if not valid_patterns:
            return None
        
        # Get the strongest pattern
        strongest_pattern = max(valid_patterns, key=lambda p: p['adjusted_strength'])
        
        # Determine signal direction
        if strongest_pattern['bullish'] is True:
            signal_direction = TradeDirection.LONG
        elif strongest_pattern['bullish'] is False:
            signal_direction = TradeDirection.SHORT
        else:
            # For neutral patterns like doji, use market structure
            if market_structure['structure'] == 'uptrend':
                signal_direction = TradeDirection.LONG
            elif market_structure['structure'] == 'downtrend':
                signal_direction = TradeDirection.SHORT
            else:
                return None  # No clear direction
        
        # Calculate entry, SL, and TP
        current_close = latest_candle['close']
        current_high = latest_candle['high']
        current_low = latest_candle['low']
        atr = latest_candle.get(f'ATR_{self.config["atr_period"]}')
        
        if pd.isna(atr):
            atr = (current_high - current_low) * 2  # Fallback ATR estimate
        
        entry_price = current_close
        
        if signal_direction == TradeDirection.LONG:
            stop_loss = current_low - (self.config['atr_multiplier_sl'] * atr)
            risk_per_unit = entry_price - stop_loss
        else:  # SHORT
            stop_loss = current_high + (self.config['atr_multiplier_sl'] * atr)
            risk_per_unit = stop_loss - entry_price
        
        if risk_per_unit <= 0:
            return None
        
        take_profit = (entry_price + (self.config['tp_rr_ratio'] * risk_per_unit) 
                      if signal_direction == TradeDirection.LONG 
                      else entry_price - (self.config['tp_rr_ratio'] * risk_per_unit))
        
        # Calculate final signal strength
        signal_strength = strongest_pattern['adjusted_strength']
        
        if signal_strength < self.config['min_signal_strength']:
            return None
        
        return TradingSignal(
            symbol=symbol,
            direction=signal_direction,
            entry_price=float(entry_price),
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
            suggested_leverage=self.config['default_leverage'],
            signal_strength=round(signal_strength, 2),
            strategy_name=f"{self.name}_{strongest_pattern['pattern']}",
            trigger_price=float(current_close),
            timestamp=datetime.now(timezone.utc)
        )
    
    def _pattern_aligns_with_structure(self, pattern: Dict[str, Any], structure: Dict[str, Any]) -> bool:
        """Check if pattern aligns with market structure."""
        pattern_bullish = pattern['bullish']
        structure_type = structure['structure']
        
        if pattern_bullish is None:  # Neutral patterns
            return True
        
        # Bullish patterns in uptrend or bearish patterns in downtrend
        return ((pattern_bullish and structure_type == 'uptrend') or
                (not pattern_bullish and structure_type == 'downtrend'))
    
    def validate_market_conditions(
        self,
        market_regime_info: MarketRegimeInfo,
        df_with_indicators: pd.DataFrame
    ) -> bool:
        """Validate if market conditions are suitable for price action trading."""
        # Price action works in all market conditions but prefer normal volatility
        return market_regime_info.volatility_level != "HIGH"
    
    def get_required_indicators(self) -> List[str]:
        """Get required indicators for this strategy."""
        return [f'ATR_{self.config["atr_period"]}']
    
    def get_minimum_data_points(self) -> int:
        """Get minimum data points required."""
        return max(20, self.config['atr_period'])