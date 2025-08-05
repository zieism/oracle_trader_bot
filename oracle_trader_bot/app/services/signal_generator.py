# app/services/signal_generator.py
"""Signal generation service that coordinates strategy execution."""
import logging
from typing import Optional, Dict, Any, List
import pandas as pd

from app.schemas.trading_signal import TradingSignal
from app.schemas.market_regime_schemas import MarketRegimeInfo
from app.strategies.trend_following_strategy import generate_trend_signal
from app.strategies.range_trading_strategy import generate_range_signal
from app.core.config import settings

logger = logging.getLogger(__name__)


class SignalGenerator:
    """Generates trading signals based on market conditions and available strategies."""
    
    def __init__(self):
        self.strategies = {
            'trend_following': generate_trend_signal,
            'range_trading': generate_range_signal
        }
    
    async def generate_signal(
        self,
        symbol: str,
        df_with_indicators: pd.DataFrame,
        market_regime_info: MarketRegimeInfo,
        current_open_positions: List[str],
        bot_config: Any
    ) -> Optional[TradingSignal]:
        """
        Generates a trading signal based on market regime and strategy selection.
        
        Args:
            symbol: Trading symbol
            df_with_indicators: DataFrame with technical indicators
            market_regime_info: Current market regime information
            current_open_positions: List of symbols with open positions
            bot_config: Bot configuration settings
            
        Returns:
            TradingSignal if conditions are met, None otherwise
        """
        if symbol in current_open_positions:
            logger.debug(f"SignalGenerator: Symbol {symbol} has open position, skipping")
            return None
        
        # Strategy selection based on market regime
        if market_regime_info.is_trending:
            logger.info(f"SignalGenerator: Using trend-following strategy for {symbol}")
            return await self._generate_trend_signal(
                symbol, df_with_indicators, market_regime_info, current_open_positions
            )
        elif (market_regime_info.trend_direction == "SIDEWAYS" and 
              bot_config.trade_amount_mode != "HIGH" and 
              market_regime_info.volatility_level != "HIGH"):
            logger.info(f"SignalGenerator: Using range-trading strategy for {symbol}")
            return await self._generate_range_signal(
                symbol, df_with_indicators, market_regime_info, current_open_positions
            )
        else:
            logger.info(f"SignalGenerator: No suitable strategy for {symbol} in regime: {market_regime_info.descriptive_label}")
            return None
    
    async def _generate_trend_signal(
        self,
        symbol: str,
        df_with_indicators: pd.DataFrame,
        market_regime_info: MarketRegimeInfo,
        current_open_positions: List[str]
    ) -> Optional[TradingSignal]:
        """Generates trend-following signal."""
        try:
            return generate_trend_signal(
                symbol=symbol,
                df_with_indicators=df_with_indicators,
                market_regime_info=market_regime_info,
                current_open_positions_symbols=current_open_positions,
                ema_fast_period=settings.TREND_EMA_FAST_PERIOD,
                ema_medium_period=settings.TREND_EMA_MEDIUM_PERIOD,
                ema_slow_period=settings.TREND_EMA_SLOW_PERIOD,
                rsi_period=settings.TREND_RSI_PERIOD,
                rsi_overbought=settings.TREND_RSI_OVERBOUGHT,
                rsi_oversold=settings.TREND_RSI_OVERSOLD,
                rsi_bull_zone_min=settings.TREND_RSI_BULL_ZONE_MIN,
                rsi_bear_zone_max=settings.TREND_RSI_BEAR_ZONE_MAX,
                atr_period_sl_tp=settings.TREND_ATR_PERIOD_SL_TP,
                atr_multiplier_sl=settings.TREND_ATR_MULTIPLIER_SL,
                tp_rr_ratio=settings.TREND_TP_RR_RATIO,
                min_signal_strength=settings.TREND_MIN_SIGNAL_STRENGTH,
                leverage_tiers_list=settings.TREND_LEVERAGE_TIERS,
                default_bot_leverage=settings.BOT_DEFAULT_LEVERAGE
            )
        except Exception as e:
            logger.error(f"SignalGenerator: Error generating trend signal for {symbol}: {e}", exc_info=True)
            return None
    
    async def _generate_range_signal(
        self,
        symbol: str,
        df_with_indicators: pd.DataFrame,
        market_regime_info: MarketRegimeInfo,
        current_open_positions: List[str]
    ) -> Optional[TradingSignal]:
        """Generates range-trading signal."""
        try:
            return generate_range_signal(
                symbol=symbol,
                df_with_indicators=df_with_indicators,
                market_regime_info=market_regime_info,
                current_open_positions_symbols=current_open_positions,
                rsi_period=settings.RANGE_RSI_PERIOD,
                rsi_overbought_entry=settings.RANGE_RSI_OVERBOUGHT,
                rsi_oversold_entry=settings.RANGE_RSI_OVERSOLD,
                bbands_period=settings.RANGE_BBANDS_PERIOD,
                bbands_std_dev=settings.RANGE_BBANDS_STD_DEV,
                atr_period_sl_tp=settings.RANGE_ATR_PERIOD_SL_TP,
                atr_multiplier_sl=settings.RANGE_ATR_MULTIPLIER_SL,
                tp_rr_ratio=settings.RANGE_TP_RR_RATIO,
                min_signal_strength=settings.RANGE_MIN_SIGNAL_STRENGTH,
                leverage_tiers_list=settings.RANGE_LEVERAGE_TIERS,
                default_bot_leverage=settings.BOT_DEFAULT_LEVERAGE
            )
        except Exception as e:
            logger.error(f"SignalGenerator: Error generating range signal for {symbol}: {e}", exc_info=True)
            return None
    
    def get_available_strategies(self) -> List[str]:
        """Returns list of available strategy names."""
        return list(self.strategies.keys())
    
    def add_strategy(self, name: str, strategy_func):
        """Adds a new strategy to the available strategies."""
        self.strategies[name] = strategy_func
        logger.info(f"SignalGenerator: Added strategy '{name}'")
    
    def remove_strategy(self, name: str):
        """Removes a strategy from available strategies."""
        if name in self.strategies:
            del self.strategies[name]
            logger.info(f"SignalGenerator: Removed strategy '{name}'")