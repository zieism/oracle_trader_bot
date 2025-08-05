# app/analysis/multi_timeframe.py
"""Multi-timeframe analysis for enhanced trading signals."""
import logging
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from app.exchange_clients.kucoin_futures_client import KucoinFuturesClient
from app.indicators.technical_indicators import calculate_indicators
from app.analysis.market_regime import determine_market_regime
from app.schemas.market_regime_schemas import MarketRegimeInfo
from app.core.config import settings

logger = logging.getLogger(__name__)


class MultiTimeframeAnalyzer:
    """Analyzes market conditions across multiple timeframes."""
    
    def __init__(self, kucoin_client: KucoinFuturesClient):
        self.kucoin_client = kucoin_client
        self.timeframes = {
            'primary': settings.PRIMARY_TIMEFRAME_BOT,  # Default H1
            'secondary': '5m'  # M5 for higher resolution analysis
        }
        self.cache = {}
        self.cache_ttl_seconds = 300  # 5 minutes cache
    
    async def get_multi_timeframe_analysis(
        self, 
        symbol: str,
        candle_limit: int = 200
    ) -> Dict[str, Any]:
        """
        Performs multi-timeframe analysis combining H1 and M5 data.
        
        Returns:
            Dictionary containing analysis for both timeframes and combined insights
        """
        try:
            cache_key = f"{symbol}_mtf_analysis"
            if self._is_cache_valid(cache_key):
                logger.debug(f"MultiTimeframe: Using cached analysis for {symbol}")
                return self.cache[cache_key]['data']
            
            # Fetch data for both timeframes
            primary_data = await self.kucoin_client.fetch_ohlcv(
                symbol, self.timeframes['primary'], limit=candle_limit
            )
            secondary_data = await self.kucoin_client.fetch_ohlcv(
                symbol, self.timeframes['secondary'], limit=candle_limit * 2  # More data for lower timeframe
            )
            
            if not primary_data or not secondary_data:
                logger.warning(f"MultiTimeframe: Insufficient data for {symbol}")
                return {}
            
            # Calculate indicators for both timeframes
            primary_df = self._calculate_timeframe_indicators(primary_data, 'primary')
            secondary_df = self._calculate_timeframe_indicators(secondary_data, 'secondary')
            
            if primary_df is None or secondary_df is None:
                logger.error(f"MultiTimeframe: Failed to calculate indicators for {symbol}")
                return {}
            
            # Determine market regimes for both timeframes
            primary_regime = self._get_market_regime(primary_df)
            secondary_regime = self._get_market_regime(secondary_df)
            
            # Combine analysis
            combined_analysis = self._combine_timeframe_analysis(
                symbol, primary_df, secondary_df, primary_regime, secondary_regime
            )
            
            # Cache the result
            self.cache[cache_key] = {
                'data': combined_analysis,
                'timestamp': datetime.now(timezone.utc)
            }
            
            return combined_analysis
            
        except Exception as e:
            logger.error(f"MultiTimeframe: Error analyzing {symbol}: {e}", exc_info=True)
            return {}
    
    def _calculate_timeframe_indicators(
        self, 
        ohlcv_data: List[List], 
        timeframe_type: str
    ) -> Optional[pd.DataFrame]:
        """Calculates indicators for a specific timeframe."""
        try:
            # Adjust periods based on timeframe
            multiplier = 1 if timeframe_type == 'primary' else 12  # 12x for 5m vs 1h
            
            return calculate_indicators(
                ohlcv_data,
                ema_fast_period=max(1, settings.TREND_EMA_FAST_PERIOD // multiplier),
                ema_medium_period=max(1, settings.TREND_EMA_MEDIUM_PERIOD // multiplier),
                ema_slow_period=max(1, settings.TREND_EMA_SLOW_PERIOD // multiplier),
                rsi_period=max(1, settings.TREND_RSI_PERIOD // multiplier),
                macd_fast_period=max(1, settings.TREND_MACD_FAST // multiplier),
                macd_slow_period=max(1, settings.TREND_MACD_SLOW // multiplier),
                macd_signal_period=max(1, settings.TREND_MACD_SIGNAL // multiplier),
                bbands_period=max(1, settings.REGIME_BBW_PERIOD // multiplier),
                bbands_std_dev=settings.REGIME_BBW_STD_DEV,
                atr_period=max(1, settings.TREND_ATR_PERIOD_SL_TP // multiplier),
                vol_sma_period=max(1, 20 // multiplier),
                adx_period=max(1, settings.REGIME_ADX_PERIOD // multiplier)
            )
        except Exception as e:
            logger.error(f"MultiTimeframe: Error calculating {timeframe_type} indicators: {e}", exc_info=True)
            return None
    
    def _get_market_regime(self, df: pd.DataFrame) -> MarketRegimeInfo:
        """Gets market regime for a timeframe."""
        return determine_market_regime(
            df,
            adx_period=settings.REGIME_ADX_PERIOD,
            adx_weak_trend_threshold=settings.REGIME_ADX_WEAK_TREND_THRESHOLD,
            adx_strong_trend_threshold=settings.REGIME_ADX_STRONG_TREND_THRESHOLD,
            bbands_period_for_bbw=settings.REGIME_BBW_PERIOD,
            bbands_std_dev_for_bbw=settings.REGIME_BBW_STD_DEV,
            bbw_low_threshold=settings.REGIME_BBW_LOW_THRESHOLD,
            bbw_high_threshold=settings.REGIME_BBW_HIGH_THRESHOLD
        )
    
    def _combine_timeframe_analysis(
        self,
        symbol: str,
        primary_df: pd.DataFrame,
        secondary_df: pd.DataFrame,
        primary_regime: MarketRegimeInfo,
        secondary_regime: MarketRegimeInfo
    ) -> Dict[str, Any]:
        """Combines analysis from multiple timeframes."""
        
        # Get latest data points
        primary_latest = primary_df.iloc[-1]
        secondary_latest = secondary_df.iloc[-1]
        
        # Trend confluence analysis
        trend_confluence = self._analyze_trend_confluence(primary_regime, secondary_regime)
        
        # Momentum analysis
        momentum_analysis = self._analyze_momentum_confluence(primary_latest, secondary_latest)
        
        # Volume profile analysis
        volume_analysis = self._analyze_volume_profile(primary_df, secondary_df)
        
        # Support/Resistance levels
        sr_levels = self._identify_support_resistance_levels(primary_df, secondary_df)
        
        # Overall signal strength
        combined_strength = self._calculate_combined_signal_strength(
            trend_confluence, momentum_analysis, volume_analysis
        )
        
        return {
            'symbol': symbol,
            'timestamp': datetime.now(timezone.utc),
            'timeframes': {
                'primary': {
                    'timeframe': self.timeframes['primary'],
                    'regime': primary_regime,
                    'latest_data': primary_latest.to_dict()
                },
                'secondary': {
                    'timeframe': self.timeframes['secondary'],
                    'regime': secondary_regime,
                    'latest_data': secondary_latest.to_dict()
                }
            },
            'confluence_analysis': {
                'trend_confluence': trend_confluence,
                'momentum_confluence': momentum_analysis,
                'volume_analysis': volume_analysis,
                'support_resistance': sr_levels,
                'combined_signal_strength': combined_strength
            },
            'recommendations': self._generate_mtf_recommendations(
                trend_confluence, momentum_analysis, combined_strength
            )
        }
    
    def _analyze_trend_confluence(
        self,
        primary_regime: MarketRegimeInfo,
        secondary_regime: MarketRegimeInfo
    ) -> Dict[str, Any]:
        """Analyzes trend confluence between timeframes."""
        
        # Check if trends align
        trends_align = primary_regime.trend_direction == secondary_regime.trend_direction
        
        # Strength assessment
        primary_strength = "strong" if primary_regime.is_strongly_trending else ("weak" if primary_regime.is_trending else "none")
        secondary_strength = "strong" if secondary_regime.is_strongly_trending else ("weak" if secondary_regime.is_trending else "none")
        
        # Overall confluence score
        confluence_score = 0.0
        if trends_align:
            confluence_score += 0.5
            if primary_regime.is_trending and secondary_regime.is_trending:
                confluence_score += 0.3
                if primary_regime.is_strongly_trending or secondary_regime.is_strongly_trending:
                    confluence_score += 0.2
        
        return {
            'trends_align': trends_align,
            'primary_trend': primary_regime.trend_direction,
            'secondary_trend': secondary_regime.trend_direction,
            'primary_strength': primary_strength,
            'secondary_strength': secondary_strength,
            'confluence_score': confluence_score,
            'confidence_level': 'high' if confluence_score > 0.7 else ('medium' if confluence_score > 0.4 else 'low')
        }
    
    def _analyze_momentum_confluence(
        self,
        primary_latest: pd.Series,
        secondary_latest: pd.Series
    ) -> Dict[str, Any]:
        """Analyzes momentum confluence between timeframes."""
        
        # Extract momentum indicators
        primary_rsi = primary_latest.get('RSI_14', np.nan)
        secondary_rsi = secondary_latest.get('RSI_14', np.nan)
        
        primary_macd = primary_latest.get(f'MACD_{settings.TREND_MACD_FAST}_{settings.TREND_MACD_SLOW}_{settings.TREND_MACD_SIGNAL}', np.nan)
        primary_macd_signal = primary_latest.get(f'MACDs_{settings.TREND_MACD_FAST}_{settings.TREND_MACD_SLOW}_{settings.TREND_MACD_SIGNAL}', np.nan)
        
        secondary_macd = secondary_latest.get(f'MACD_{settings.TREND_MACD_FAST}_{settings.TREND_MACD_SLOW}_{settings.TREND_MACD_SIGNAL}', np.nan)
        secondary_macd_signal = secondary_latest.get(f'MACDs_{settings.TREND_MACD_FAST}_{settings.TREND_MACD_SLOW}_{settings.TREND_MACD_SIGNAL}', np.nan)
        
        # RSI analysis
        rsi_bullish = False
        rsi_bearish = False
        if not pd.isna(primary_rsi) and not pd.isna(secondary_rsi):
            rsi_bullish = primary_rsi > 50 and secondary_rsi > 50
            rsi_bearish = primary_rsi < 50 and secondary_rsi < 50
        
        # MACD analysis
        macd_bullish = False
        macd_bearish = False
        if not pd.isna(primary_macd) and not pd.isna(secondary_macd):
            macd_bullish = (primary_macd > primary_macd_signal) and (secondary_macd > secondary_macd_signal)
            macd_bearish = (primary_macd < primary_macd_signal) and (secondary_macd < secondary_macd_signal)
        
        # Momentum score
        momentum_score = 0.0
        if rsi_bullish and macd_bullish:
            momentum_score = 0.8
        elif rsi_bearish and macd_bearish:
            momentum_score = -0.8
        elif rsi_bullish or macd_bullish:
            momentum_score = 0.4
        elif rsi_bearish or macd_bearish:
            momentum_score = -0.4
        
        return {
            'rsi_confluence': {
                'primary_rsi': primary_rsi,
                'secondary_rsi': secondary_rsi,
                'bullish_alignment': rsi_bullish,
                'bearish_alignment': rsi_bearish
            },
            'macd_confluence': {
                'primary_bullish': primary_macd > primary_macd_signal if not pd.isna(primary_macd) else None,
                'secondary_bullish': secondary_macd > secondary_macd_signal if not pd.isna(secondary_macd) else None,
                'bullish_alignment': macd_bullish,
                'bearish_alignment': macd_bearish
            },
            'momentum_score': momentum_score,
            'momentum_direction': 'bullish' if momentum_score > 0.2 else ('bearish' if momentum_score < -0.2 else 'neutral')
        }
    
    def _analyze_volume_profile(
        self,
        primary_df: pd.DataFrame,
        secondary_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Analyzes volume patterns across timeframes."""
        
        # Calculate volume metrics
        primary_vol_sma = primary_df['VOL_SMA_20'].iloc[-5:].mean() if 'VOL_SMA_20' in primary_df.columns else np.nan
        secondary_vol_sma = secondary_df['VOL_SMA_20'].iloc[-5:].mean() if 'VOL_SMA_20' in secondary_df.columns else np.nan
        
        current_primary_vol = primary_df['volume'].iloc[-1] if 'volume' in primary_df.columns else np.nan
        current_secondary_vol = secondary_df['volume'].iloc[-1] if 'volume' in secondary_df.columns else np.nan
        
        # Volume confirmation
        volume_increasing = False
        if not pd.isna(primary_vol_sma) and not pd.isna(current_primary_vol):
            volume_increasing = current_primary_vol > primary_vol_sma
        
        return {
            'primary_volume_trend': 'increasing' if volume_increasing else 'decreasing',
            'volume_confirmation': volume_increasing,
            'relative_volume': {
                'primary_ratio': current_primary_vol / primary_vol_sma if not pd.isna(primary_vol_sma) and primary_vol_sma > 0 else 1.0,
                'secondary_ratio': current_secondary_vol / secondary_vol_sma if not pd.isna(secondary_vol_sma) and secondary_vol_sma > 0 else 1.0
            }
        }
    
    def _identify_support_resistance_levels(
        self,
        primary_df: pd.DataFrame,
        secondary_df: pd.DataFrame
    ) -> Dict[str, List[float]]:
        """Identifies key support and resistance levels."""
        
        # Simple pivot point identification
        recent_highs = primary_df['high'].tail(20).nlargest(3).tolist()
        recent_lows = primary_df['low'].tail(20).nsmallest(3).tolist()
        
        return {
            'resistance_levels': recent_highs,
            'support_levels': recent_lows,
            'current_price': float(primary_df['close'].iloc[-1])
        }
    
    def _calculate_combined_signal_strength(
        self,
        trend_confluence: Dict,
        momentum_analysis: Dict,
        volume_analysis: Dict
    ) -> float:
        """Calculates overall signal strength from multi-timeframe analysis."""
        
        strength = 0.0
        
        # Trend confluence contribution (40%)
        strength += trend_confluence['confluence_score'] * 0.4
        
        # Momentum contribution (40%)
        momentum_strength = abs(momentum_analysis['momentum_score'])
        strength += momentum_strength * 0.4
        
        # Volume confirmation (20%)
        if volume_analysis['volume_confirmation']:
            strength += 0.2
        
        return min(1.0, strength)  # Cap at 1.0
    
    def _generate_mtf_recommendations(
        self,
        trend_confluence: Dict,
        momentum_analysis: Dict,
        combined_strength: float
    ) -> Dict[str, Any]:
        """Generates trading recommendations based on multi-timeframe analysis."""
        
        recommendations = {
            'action': 'HOLD',
            'confidence': 'LOW',
            'reasons': [],
            'risk_level': 'MEDIUM'
        }
        
        # Determine action based on confluence
        if trend_confluence['trends_align'] and combined_strength > 0.6:
            if momentum_analysis['momentum_direction'] == 'bullish':
                recommendations['action'] = 'BUY'
                recommendations['reasons'].append('Bullish trend and momentum confluence')
            elif momentum_analysis['momentum_direction'] == 'bearish':
                recommendations['action'] = 'SELL'
                recommendations['reasons'].append('Bearish trend and momentum confluence')
        
        # Set confidence level
        if combined_strength > 0.8:
            recommendations['confidence'] = 'HIGH'
        elif combined_strength > 0.6:
            recommendations['confidence'] = 'MEDIUM'
        
        # Adjust risk level
        if trend_confluence['confidence_level'] == 'high' and combined_strength > 0.7:
            recommendations['risk_level'] = 'LOW'
        elif trend_confluence['confidence_level'] == 'low' or combined_strength < 0.4:
            recommendations['risk_level'] = 'HIGH'
        
        return recommendations
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Checks if cached data is still valid."""
        if cache_key not in self.cache:
            return False
        
        cache_time = self.cache[cache_key]['timestamp']
        current_time = datetime.now(timezone.utc)
        return (current_time - cache_time).total_seconds() < self.cache_ttl_seconds
    
    def clear_cache(self):
        """Clears the analysis cache."""
        self.cache.clear()
        logger.info("MultiTimeframe: Cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Returns cache statistics."""
        return {
            'cached_symbols': len(self.cache),
            'cache_ttl_seconds': self.cache_ttl_seconds,
            'symbols': list(self.cache.keys())
        }