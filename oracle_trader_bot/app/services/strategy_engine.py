# app/services/strategy_engine.py
"""Strategy selection and execution engine."""
import logging
from typing import Optional, Dict, Any, List
import pandas as pd

from app.schemas.trading_signal import TradingSignal
from app.schemas.market_regime_schemas import MarketRegimeInfo
from app.services.signal_generator import SignalGenerator
from app.analysis.market_regime import determine_market_regime
from app.indicators.technical_indicators import calculate_indicators
from app.core.config import settings

logger = logging.getLogger(__name__)


class StrategyEngine:
    """Coordinates strategy selection and execution based on market conditions."""
    
    def __init__(self):
        self.signal_generator = SignalGenerator()
        self.strategy_performance = {}
        self.market_condition_cache = {}
    
    async def analyze_and_generate_signal(
        self,
        symbol: str,
        ohlcv_data: List[List],
        current_open_positions: List[str],
        bot_config: Any
    ) -> Optional[TradingSignal]:
        """
        Main method that analyzes market conditions and generates trading signals.
        
        Args:
            symbol: Trading symbol
            ohlcv_data: OHLCV candle data
            current_open_positions: List of symbols with open positions
            bot_config: Bot configuration
            
        Returns:
            TradingSignal if conditions are met, None otherwise
        """
        try:
            # Validate data sufficiency
            min_data_needed = self._get_minimum_data_requirement()
            if not ohlcv_data or len(ohlcv_data) < min_data_needed:
                logger.warning(f"StrategyEngine: Insufficient data for {symbol}. Need {min_data_needed}, have {len(ohlcv_data) if ohlcv_data else 0}")
                return None
            
            # Calculate technical indicators
            df_with_indicators = self._calculate_indicators(ohlcv_data)
            if df_with_indicators is None or df_with_indicators.empty:
                logger.error(f"StrategyEngine: Failed to calculate indicators for {symbol}")
                return None
            
            # Determine market regime
            market_regime_info = self._determine_market_regime(df_with_indicators)
            logger.info(f"StrategyEngine: Market regime for {symbol}: {market_regime_info.descriptive_label}")
            
            # Cache market condition for performance tracking
            self.market_condition_cache[symbol] = {
                'regime': market_regime_info,
                'timestamp': pd.Timestamp.now()
            }
            
            # Generate signal based on market conditions
            signal = await self.signal_generator.generate_signal(
                symbol=symbol,
                df_with_indicators=df_with_indicators,
                market_regime_info=market_regime_info,
                current_open_positions=current_open_positions,
                bot_config=bot_config
            )
            
            if signal:
                logger.info(f"StrategyEngine: Generated {signal.direction.value} signal for {symbol} using {signal.strategy_name}")
                self._track_signal_generation(symbol, signal, market_regime_info)
            
            return signal
            
        except Exception as e:
            logger.error(f"StrategyEngine: Error analyzing {symbol}: {e}", exc_info=True)
            return None
    
    def _get_minimum_data_requirement(self) -> int:
        """Returns the minimum number of candles needed for analysis."""
        return max(
            settings.TREND_EMA_SLOW_PERIOD,
            settings.RANGE_BBANDS_PERIOD,
            settings.TREND_RSI_PERIOD,
            settings.TREND_ATR_PERIOD_SL_TP,
            settings.REGIME_ADX_PERIOD,
            (settings.TREND_MACD_SLOW + settings.TREND_MACD_SIGNAL)
        )
    
    def _calculate_indicators(self, ohlcv_data: List[List]) -> Optional[pd.DataFrame]:
        """Calculates technical indicators for the given OHLCV data."""
        try:
            return calculate_indicators(
                ohlcv_data,
                ema_fast_period=settings.TREND_EMA_FAST_PERIOD,
                ema_medium_period=settings.TREND_EMA_MEDIUM_PERIOD,
                ema_slow_period=settings.TREND_EMA_SLOW_PERIOD,
                rsi_period=settings.TREND_RSI_PERIOD,
                macd_fast_period=settings.TREND_MACD_FAST,
                macd_slow_period=settings.TREND_MACD_SLOW,
                macd_signal_period=settings.TREND_MACD_SIGNAL,
                bbands_period=settings.REGIME_BBW_PERIOD,
                bbands_std_dev=float(settings.REGIME_BBW_STD_DEV),
                atr_period=settings.TREND_ATR_PERIOD_SL_TP,
                vol_sma_period=20,
                adx_period=settings.REGIME_ADX_PERIOD
            )
        except Exception as e:
            logger.error(f"StrategyEngine: Error calculating indicators: {e}", exc_info=True)
            return None
    
    def _determine_market_regime(self, df_with_indicators: pd.DataFrame) -> MarketRegimeInfo:
        """Determines the current market regime."""
        return determine_market_regime(
            df_with_indicators,
            adx_period=settings.REGIME_ADX_PERIOD,
            adx_weak_trend_threshold=settings.REGIME_ADX_WEAK_TREND_THRESHOLD,
            adx_strong_trend_threshold=settings.REGIME_ADX_STRONG_TREND_THRESHOLD,
            bbands_period_for_bbw=settings.REGIME_BBW_PERIOD,
            bbands_std_dev_for_bbw=float(settings.REGIME_BBW_STD_DEV),
            bbw_low_threshold=settings.REGIME_BBW_LOW_THRESHOLD,
            bbw_high_threshold=settings.REGIME_BBW_HIGH_THRESHOLD
        )
    
    def _track_signal_generation(
        self, 
        symbol: str, 
        signal: TradingSignal, 
        market_regime: MarketRegimeInfo
    ):
        """Tracks signal generation for performance analysis."""
        strategy_name = signal.strategy_name
        
        if strategy_name not in self.strategy_performance:
            self.strategy_performance[strategy_name] = {
                'signals_generated': 0,
                'by_regime': {},
                'by_symbol': {},
                'latest_signals': []
            }
        
        perf = self.strategy_performance[strategy_name]
        perf['signals_generated'] += 1
        
        # Track by regime
        regime_key = market_regime.descriptive_label
        perf['by_regime'][regime_key] = perf['by_regime'].get(regime_key, 0) + 1
        
        # Track by symbol
        perf['by_symbol'][symbol] = perf['by_symbol'].get(symbol, 0) + 1
        
        # Store latest signals (keep last 10)
        signal_info = {
            'symbol': symbol,
            'direction': signal.direction.value,
            'strength': signal.signal_strength,
            'regime': regime_key,
            'timestamp': signal.timestamp
        }
        perf['latest_signals'].append(signal_info)
        if len(perf['latest_signals']) > 10:
            perf['latest_signals'] = perf['latest_signals'][-10:]
    
    def get_strategy_performance(self) -> Dict[str, Any]:
        """Returns strategy performance statistics."""
        return self.strategy_performance.copy()
    
    def get_market_conditions_summary(self) -> Dict[str, Any]:
        """Returns summary of current market conditions across symbols."""
        summary = {
            'total_symbols': len(self.market_condition_cache),
            'regime_distribution': {},
            'volatility_distribution': {},
            'trending_count': 0,
            'ranging_count': 0
        }
        
        for symbol, data in self.market_condition_cache.items():
            regime = data['regime']
            
            # Count regime types
            regime_key = regime.descriptive_label
            summary['regime_distribution'][regime_key] = summary['regime_distribution'].get(regime_key, 0) + 1
            
            # Count volatility levels
            vol_key = regime.volatility_level or 'UNKNOWN'
            summary['volatility_distribution'][vol_key] = summary['volatility_distribution'].get(vol_key, 0) + 1
            
            # Count trending vs ranging
            if regime.is_trending:
                summary['trending_count'] += 1
            else:
                summary['ranging_count'] += 1
        
        return summary
    
    def reset_performance_tracking(self):
        """Resets performance tracking data."""
        self.strategy_performance.clear()
        logger.info("StrategyEngine: Performance tracking data reset")
    
    def add_strategy(self, name: str, strategy_func):
        """Adds a new strategy to the signal generator."""
        self.signal_generator.add_strategy(name, strategy_func)
    
    def get_available_strategies(self) -> List[str]:
        """Returns list of available strategies."""
        return self.signal_generator.get_available_strategies()