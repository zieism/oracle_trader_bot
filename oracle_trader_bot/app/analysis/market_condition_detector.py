# app/analysis/market_condition_detector.py
"""Enhanced market condition detection with ADX, ATR, Volume, and Price Action patterns."""
import logging
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from app.schemas.market_regime_schemas import MarketRegimeInfo

logger = logging.getLogger(__name__)


class MarketConditionDetector:
    """Enhanced market condition detection with multiple indicators and price action patterns."""
    
    def __init__(self):
        self.price_action_patterns = [
            'doji', 'hammer', 'shooting_star', 'engulfing_bullish', 'engulfing_bearish',
            'pin_bar_bullish', 'pin_bar_bearish', 'inside_bar', 'outside_bar'
        ]
    
    def detect_enhanced_market_conditions(
        self,
        df_with_indicators: pd.DataFrame,
        lookback_periods: int = 20
    ) -> Dict[str, Any]:
        """
        Performs comprehensive market condition analysis.
        
        Args:
            df_with_indicators: DataFrame with technical indicators
            lookback_periods: Number of periods to analyze
            
        Returns:
            Dictionary with detailed market condition analysis
        """
        if df_with_indicators is None or df_with_indicators.empty:
            return self._get_default_conditions()
        
        latest_data = df_with_indicators.tail(lookback_periods)
        current_candle = latest_data.iloc[-1]
        
        # Enhanced trend analysis
        trend_analysis = self._analyze_trend_strength(latest_data, current_candle)
        
        # Volatility analysis
        volatility_analysis = self._analyze_volatility_regime(latest_data, current_candle)
        
        # Volume analysis
        volume_analysis = self._analyze_volume_conditions(latest_data, current_candle)
        
        # Price action pattern detection
        price_action = self._detect_price_action_patterns(latest_data)
        
        # Market structure analysis
        market_structure = self._analyze_market_structure(latest_data)
        
        # Momentum analysis
        momentum_analysis = self._analyze_momentum_conditions(latest_data, current_candle)
        
        # Overall market state
        market_state = self._determine_overall_market_state(
            trend_analysis, volatility_analysis, volume_analysis, momentum_analysis
        )
        
        return {
            'timestamp': datetime.now(timezone.utc),
            'trend_analysis': trend_analysis,
            'volatility_analysis': volatility_analysis,
            'volume_analysis': volume_analysis,
            'price_action_patterns': price_action,
            'market_structure': market_structure,
            'momentum_analysis': momentum_analysis,
            'overall_market_state': market_state,
            'trading_recommendations': self._generate_trading_recommendations(
                trend_analysis, volatility_analysis, volume_analysis, price_action, market_state
            )
        }
    
    def _analyze_trend_strength(
        self,
        data: pd.DataFrame,
        current: pd.Series
    ) -> Dict[str, Any]:
        """Enhanced trend analysis using multiple indicators."""
        
        # ADX-based trend strength
        adx_col = None
        plus_di_col = None
        minus_di_col = None
        
        # Find ADX columns dynamically
        for col in data.columns:
            if col.startswith('ADX_'):
                adx_col = col
            elif col.startswith('DMP_'):
                plus_di_col = col
            elif col.startswith('DMN_'):
                minus_di_col = col
        
        adx_analysis = {}
        if adx_col and plus_di_col and minus_di_col:
            current_adx = current.get(adx_col, np.nan)
            current_plus_di = current.get(plus_di_col, np.nan)
            current_minus_di = current.get(minus_di_col, np.nan)
            
            adx_analysis = {
                'adx_value': current_adx,
                'plus_di': current_plus_di,
                'minus_di': current_minus_di,
                'trend_strength': self._classify_adx_strength(current_adx),
                'trend_direction': 'bullish' if current_plus_di > current_minus_di else 'bearish'
            }
        
        # EMA trend analysis
        ema_analysis = self._analyze_ema_trends(data, current)
        
        # Trend consistency
        trend_consistency = self._analyze_trend_consistency(data)
        
        return {
            'adx_analysis': adx_analysis,
            'ema_analysis': ema_analysis,
            'trend_consistency': trend_consistency,
            'overall_trend_score': self._calculate_trend_score(adx_analysis, ema_analysis, trend_consistency)
        }
    
    def _analyze_volatility_regime(
        self,
        data: pd.DataFrame,
        current: pd.Series
    ) -> Dict[str, Any]:
        """Enhanced volatility analysis using ATR and Bollinger Band Width."""
        
        # ATR analysis
        atr_analysis = self._analyze_atr_conditions(data, current)
        
        # Bollinger Band Width analysis
        bbw_analysis = self._analyze_bbw_conditions(data, current)
        
        # Historical volatility analysis
        hist_vol_analysis = self._analyze_historical_volatility(data)
        
        # Volatility regime classification
        volatility_regime = self._classify_volatility_regime(atr_analysis, bbw_analysis, hist_vol_analysis)
        
        return {
            'atr_analysis': atr_analysis,
            'bbw_analysis': bbw_analysis,
            'historical_volatility': hist_vol_analysis,
            'volatility_regime': volatility_regime,
            'volatility_score': self._calculate_volatility_score(atr_analysis, bbw_analysis)
        }
    
    def _analyze_volume_conditions(
        self,
        data: pd.DataFrame,
        current: pd.Series
    ) -> Dict[str, Any]:
        """Enhanced volume analysis."""
        
        if 'volume' not in data.columns:
            return {'volume_available': False}
        
        current_volume = current.get('volume', 0)
        volume_sma = data['volume'].rolling(20).mean().iloc[-1] if len(data) >= 20 else current_volume
        
        # Volume trend analysis
        volume_trend = self._analyze_volume_trend(data)
        
        # Volume breakout detection
        volume_breakout = self._detect_volume_breakout(data, current_volume, volume_sma)
        
        # Volume price relationship
        volume_price_relationship = self._analyze_volume_price_relationship(data)
        
        return {
            'volume_available': True,
            'current_volume': current_volume,
            'volume_sma_20': volume_sma,
            'volume_ratio': current_volume / volume_sma if volume_sma > 0 else 1.0,
            'volume_trend': volume_trend,
            'volume_breakout': volume_breakout,
            'volume_price_relationship': volume_price_relationship,
            'volume_score': self._calculate_volume_score(current_volume, volume_sma, volume_trend)
        }
    
    def _detect_price_action_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Detects various price action patterns."""
        
        if len(data) < 3:
            return {'patterns_detected': []}
        
        patterns_found = []
        recent_candles = data.tail(3)
        
        # Check each pattern
        for pattern_name in self.price_action_patterns:
            if self._check_pattern(pattern_name, recent_candles):
                patterns_found.append({
                    'pattern': pattern_name,
                    'strength': self._calculate_pattern_strength(pattern_name, recent_candles),
                    'bullish': self._is_pattern_bullish(pattern_name)
                })
        
        # Support and resistance levels
        support_resistance = self._identify_key_levels(data)
        
        return {
            'patterns_detected': patterns_found,
            'pattern_count': len(patterns_found),
            'bullish_patterns': [p for p in patterns_found if p['bullish']],
            'bearish_patterns': [p for p in patterns_found if not p['bullish']],
            'support_resistance': support_resistance
        }
    
    def _analyze_market_structure(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyzes market structure (higher highs, higher lows, etc.)."""
        
        if len(data) < 10:
            return {'structure_type': 'insufficient_data'}
        
        highs = data['high'].values
        lows = data['low'].values
        
        # Find recent swing highs and lows
        swing_highs = self._find_swing_points(highs, 'high')
        swing_lows = self._find_swing_points(lows, 'low')
        
        # Analyze structure
        structure_analysis = self._classify_market_structure(swing_highs, swing_lows)
        
        return {
            'swing_highs': swing_highs[-3:] if len(swing_highs) >= 3 else swing_highs,
            'swing_lows': swing_lows[-3:] if len(swing_lows) >= 3 else swing_lows,
            'structure_type': structure_analysis['type'],
            'structure_strength': structure_analysis['strength'],
            'break_of_structure': structure_analysis.get('break_detected', False)
        }
    
    def _analyze_momentum_conditions(
        self,
        data: pd.DataFrame,
        current: pd.Series
    ) -> Dict[str, Any]:
        """Analyzes momentum using RSI, MACD, and rate of change."""
        
        # RSI analysis
        rsi_analysis = self._analyze_rsi_momentum(data, current)
        
        # MACD analysis
        macd_analysis = self._analyze_macd_momentum(data, current)
        
        # Rate of change analysis
        roc_analysis = self._analyze_rate_of_change(data)
        
        # Combined momentum score
        momentum_score = self._calculate_momentum_score(rsi_analysis, macd_analysis, roc_analysis)
        
        return {
            'rsi_analysis': rsi_analysis,
            'macd_analysis': macd_analysis,
            'rate_of_change': roc_analysis,
            'momentum_score': momentum_score,
            'momentum_direction': 'bullish' if momentum_score > 0.2 else ('bearish' if momentum_score < -0.2 else 'neutral')
        }
    
    def _determine_overall_market_state(
        self,
        trend_analysis: Dict,
        volatility_analysis: Dict,
        volume_analysis: Dict,
        momentum_analysis: Dict
    ) -> Dict[str, Any]:
        """Determines the overall market state from all analyses."""
        
        # Combine scores
        trend_score = trend_analysis.get('overall_trend_score', 0)
        volatility_score = volatility_analysis.get('volatility_score', 0)
        volume_score = volume_analysis.get('volume_score', 0)
        momentum_score = momentum_analysis.get('momentum_score', 0)
        
        # Weighted overall score
        overall_score = (
            trend_score * 0.3 +
            momentum_score * 0.3 +
            volume_score * 0.2 +
            volatility_score * 0.2
        )
        
        # Market phase classification
        market_phase = self._classify_market_phase(
            trend_analysis, volatility_analysis, momentum_analysis
        )
        
        return {
            'overall_score': overall_score,
            'market_phase': market_phase,
            'confidence_level': self._calculate_confidence_level(overall_score, trend_analysis, volatility_analysis),
            'risk_level': self._assess_risk_level(volatility_analysis, trend_analysis)
        }
    
    # Helper methods for specific analyses
    def _classify_adx_strength(self, adx_value: float) -> str:
        """Classifies ADX strength."""
        if pd.isna(adx_value):
            return 'unknown'
        elif adx_value < 20:
            return 'weak'
        elif adx_value < 25:
            return 'moderate'
        elif adx_value < 40:
            return 'strong'
        else:
            return 'very_strong'
    
    def _analyze_ema_trends(self, data: pd.DataFrame, current: pd.Series) -> Dict[str, Any]:
        """Analyzes EMA trend alignment."""
        ema_cols = [col for col in data.columns if col.startswith('EMA_')]
        
        if len(ema_cols) < 2:
            return {'ema_alignment': 'insufficient_data'}
        
        ema_values = {col: current.get(col, np.nan) for col in ema_cols[:3]}  # Take first 3 EMAs
        ema_sorted = sorted(ema_values.items(), key=lambda x: int(x[0].split('_')[1]))
        
        # Check alignment
        bullish_alignment = all(
            ema_sorted[i][1] < ema_sorted[i+1][1] 
            for i in range(len(ema_sorted)-1) 
            if not pd.isna(ema_sorted[i][1]) and not pd.isna(ema_sorted[i+1][1])
        )
        
        bearish_alignment = all(
            ema_sorted[i][1] > ema_sorted[i+1][1] 
            for i in range(len(ema_sorted)-1) 
            if not pd.isna(ema_sorted[i][1]) and not pd.isna(ema_sorted[i+1][1])
        )
        
        return {
            'ema_alignment': 'bullish' if bullish_alignment else ('bearish' if bearish_alignment else 'mixed'),
            'ema_values': ema_values
        }
    
    def _get_default_conditions(self) -> Dict[str, Any]:
        """Returns default conditions when data is insufficient."""
        return {
            'timestamp': datetime.now(timezone.utc),
            'trend_analysis': {'overall_trend_score': 0},
            'volatility_analysis': {'volatility_score': 0},
            'volume_analysis': {'volume_available': False},
            'price_action_patterns': {'patterns_detected': []},
            'market_structure': {'structure_type': 'insufficient_data'},
            'momentum_analysis': {'momentum_score': 0},
            'overall_market_state': {
                'overall_score': 0,
                'market_phase': 'uncertain',
                'confidence_level': 'low',
                'risk_level': 'high'
            }
        }
    
    # Placeholder methods for complex analyses (to be implemented based on specific requirements)
    def _analyze_trend_consistency(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyzes trend consistency over time."""
        return {'consistency_score': 0.5}
    
    def _calculate_trend_score(self, adx_analysis: Dict, ema_analysis: Dict, consistency: Dict) -> float:
        """Calculates overall trend score."""
        return 0.5  # Placeholder
    
    def _analyze_atr_conditions(self, data: pd.DataFrame, current: pd.Series) -> Dict[str, Any]:
        """Analyzes ATR conditions."""
        atr_cols = [col for col in data.columns if col.startswith('ATR_')]
        if atr_cols:
            current_atr = current.get(atr_cols[0], np.nan)
            return {'current_atr': current_atr, 'atr_trend': 'neutral'}
        return {'current_atr': np.nan, 'atr_trend': 'unknown'}
    
    def _analyze_bbw_conditions(self, data: pd.DataFrame, current: pd.Series) -> Dict[str, Any]:
        """Analyzes Bollinger Band Width."""
        bbw_cols = [col for col in data.columns if col.startswith('BBB_')]
        if bbw_cols:
            current_bbw = current.get(bbw_cols[0], np.nan)
            return {'current_bbw': current_bbw, 'bbw_trend': 'neutral'}
        return {'current_bbw': np.nan, 'bbw_trend': 'unknown'}
    
    def _analyze_historical_volatility(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyzes historical volatility."""
        if 'close' in data.columns and len(data) > 1:
            returns = data['close'].pct_change().dropna()
            hist_vol = returns.std() * np.sqrt(252)  # Annualized
            return {'historical_volatility': hist_vol}
        return {'historical_volatility': np.nan}
    
    def _classify_volatility_regime(self, atr: Dict, bbw: Dict, hist_vol: Dict) -> str:
        """Classifies volatility regime."""
        return 'normal'  # Placeholder
    
    def _calculate_volatility_score(self, atr: Dict, bbw: Dict) -> float:
        """Calculates volatility score."""
        return 0.5  # Placeholder
    
    def _analyze_volume_trend(self, data: pd.DataFrame) -> str:
        """Analyzes volume trend."""
        return 'neutral'  # Placeholder
    
    def _detect_volume_breakout(self, data: pd.DataFrame, current_vol: float, vol_sma: float) -> bool:
        """Detects volume breakout."""
        return current_vol > vol_sma * 1.5  # Simple breakout detection
    
    def _analyze_volume_price_relationship(self, data: pd.DataFrame) -> str:
        """Analyzes volume-price relationship."""
        return 'neutral'  # Placeholder
    
    def _calculate_volume_score(self, current_vol: float, vol_sma: float, trend: str) -> float:
        """Calculates volume score."""
        if vol_sma > 0:
            return min(1.0, current_vol / vol_sma)
        return 0.5
    
    def _check_pattern(self, pattern_name: str, candles: pd.DataFrame) -> bool:
        """Checks for specific price action pattern."""
        # Simple doji detection as example
        if pattern_name == 'doji':
            latest = candles.iloc[-1]
            body = abs(latest['close'] - latest['open'])
            range_size = latest['high'] - latest['low']
            return body < (range_size * 0.1) if range_size > 0 else False
        return False  # Placeholder for other patterns
    
    def _calculate_pattern_strength(self, pattern_name: str, candles: pd.DataFrame) -> float:
        """Calculates pattern strength."""
        return 0.5  # Placeholder
    
    def _is_pattern_bullish(self, pattern_name: str) -> bool:
        """Determines if pattern is bullish."""
        bullish_patterns = ['hammer', 'engulfing_bullish', 'pin_bar_bullish']
        return pattern_name in bullish_patterns
    
    def _identify_key_levels(self, data: pd.DataFrame) -> Dict[str, List[float]]:
        """Identifies key support and resistance levels."""
        recent_highs = data['high'].tail(20).nlargest(3).tolist()
        recent_lows = data['low'].tail(20).nsmallest(3).tolist()
        return {'resistance': recent_highs, 'support': recent_lows}
    
    def _find_swing_points(self, values: np.ndarray, point_type: str) -> List[Tuple[int, float]]:
        """Finds swing high/low points."""
        return []  # Placeholder
    
    def _classify_market_structure(self, highs: List, lows: List) -> Dict[str, Any]:
        """Classifies market structure."""
        return {'type': 'ranging', 'strength': 0.5}  # Placeholder
    
    def _analyze_rsi_momentum(self, data: pd.DataFrame, current: pd.Series) -> Dict[str, Any]:
        """Analyzes RSI momentum."""
        rsi_cols = [col for col in data.columns if col.startswith('RSI_')]
        if rsi_cols:
            current_rsi = current.get(rsi_cols[0], 50)
            return {'current_rsi': current_rsi, 'rsi_momentum': 'neutral'}
        return {'current_rsi': 50, 'rsi_momentum': 'unknown'}
    
    def _analyze_macd_momentum(self, data: pd.DataFrame, current: pd.Series) -> Dict[str, Any]:
        """Analyzes MACD momentum."""
        return {'macd_momentum': 'neutral'}  # Placeholder
    
    def _analyze_rate_of_change(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyzes rate of change."""
        return {'roc_momentum': 'neutral'}  # Placeholder
    
    def _calculate_momentum_score(self, rsi: Dict, macd: Dict, roc: Dict) -> float:
        """Calculates momentum score."""
        return 0.0  # Placeholder
    
    def _classify_market_phase(self, trend: Dict, volatility: Dict, momentum: Dict) -> str:
        """Classifies market phase."""
        return 'consolidation'  # Placeholder
    
    def _calculate_confidence_level(self, score: float, trend: Dict, volatility: Dict) -> str:
        """Calculates confidence level."""
        if abs(score) > 0.7:
            return 'high'
        elif abs(score) > 0.4:
            return 'medium'
        else:
            return 'low'
    
    def _assess_risk_level(self, volatility: Dict, trend: Dict) -> str:
        """Assesses risk level."""
        vol_score = volatility.get('volatility_score', 0.5)
        if vol_score > 0.7:
            return 'high'
        elif vol_score > 0.4:
            return 'medium'
        else:
            return 'low'
    
    def _generate_trading_recommendations(
        self,
        trend: Dict,
        volatility: Dict,
        volume: Dict,
        price_action: Dict,
        market_state: Dict
    ) -> Dict[str, Any]:
        """Generates trading recommendations based on all analyses."""
        return {
            'primary_recommendation': 'HOLD',
            'confidence': market_state.get('confidence_level', 'low'),
            'risk_assessment': market_state.get('risk_level', 'medium'),
            'key_factors': [
                f"Market phase: {market_state.get('market_phase', 'uncertain')}",
                f"Trend score: {trend.get('overall_trend_score', 0):.2f}",
                f"Volatility: {volatility.get('volatility_score', 0):.2f}"
            ]
        }