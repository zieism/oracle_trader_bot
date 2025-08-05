# app/market_data/sentiment_analyzer.py
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SentimentType(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"


@dataclass
class SentimentReading:
    timestamp: datetime
    symbol: str
    sentiment: SentimentType
    confidence: float  # 0.0 to 1.0
    score: float  # -1.0 (very bearish) to 1.0 (very bullish)
    source: str
    data: Dict


class MarketSentimentAnalyzer:
    """
    Market sentiment analysis using basic technical indicators and volume patterns.
    In production, this could integrate with news APIs, social media sentiment, etc.
    """
    
    def __init__(self):
        self.logger = logger
        self.sentiment_history: List[SentimentReading] = []
    
    async def analyze_market_sentiment(
        self, 
        symbol: str,
        price_data: List[Dict],
        volume_data: Optional[List[Dict]] = None
    ) -> SentimentReading:
        """
        Analyze market sentiment based on price action and volume.
        
        Args:
            symbol: Trading symbol
            price_data: List of price candles (OHLCV)
            volume_data: Optional volume data
            
        Returns:
            SentimentReading with analysis results
        """
        try:
            if len(price_data) < 20:
                return self._neutral_sentiment(symbol, "Insufficient data")
            
            # Calculate sentiment components
            price_momentum = self._analyze_price_momentum(price_data)
            volume_sentiment = self._analyze_volume_pattern(volume_data or [])
            volatility_sentiment = self._analyze_volatility(price_data)
            
            # Combine sentiment signals
            combined_score = (
                price_momentum * 0.5 +
                volume_sentiment * 0.3 +
                volatility_sentiment * 0.2
            )
            
            # Determine sentiment type and confidence
            if combined_score > 0.3:
                sentiment = SentimentType.BULLISH
                confidence = min(combined_score, 1.0)
            elif combined_score < -0.3:
                sentiment = SentimentType.BEARISH
                confidence = min(abs(combined_score), 1.0)
            elif abs(combined_score) > 0.1:
                sentiment = SentimentType.MIXED
                confidence = abs(combined_score)
            else:
                sentiment = SentimentType.NEUTRAL
                confidence = 0.5
            
            sentiment_reading = SentimentReading(
                timestamp=datetime.utcnow(),
                symbol=symbol,
                sentiment=sentiment,
                confidence=confidence,
                score=combined_score,
                source="technical_analysis",
                data={
                    "price_momentum": price_momentum,
                    "volume_sentiment": volume_sentiment,
                    "volatility_sentiment": volatility_sentiment,
                    "data_points": len(price_data)
                }
            )
            
            # Store reading
            self.sentiment_history.append(sentiment_reading)
            
            # Limit history size
            if len(self.sentiment_history) > 1000:
                self.sentiment_history = self.sentiment_history[-500:]
            
            self.logger.info(f"Sentiment analysis for {symbol}: {sentiment.value} "
                           f"(score: {combined_score:.3f}, confidence: {confidence:.3f})")
            
            return sentiment_reading
            
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment for {symbol}: {e}")
            return self._neutral_sentiment(symbol, f"Analysis error: {str(e)}")
    
    def _analyze_price_momentum(self, price_data: List[Dict]) -> float:
        """Analyze price momentum from recent candles."""
        try:
            if len(price_data) < 10:
                return 0.0
            
            recent_closes = [float(candle.get('close', 0)) for candle in price_data[-10:]]
            
            # Calculate simple momentum indicators
            short_avg = sum(recent_closes[-5:]) / 5
            long_avg = sum(recent_closes) / len(recent_closes)
            
            # Price change momentum
            price_change = (recent_closes[-1] - recent_closes[0]) / recent_closes[0]
            
            # Trend momentum
            trend_momentum = (short_avg - long_avg) / long_avg
            
            # Combine momentum signals
            momentum_score = (price_change * 0.6 + trend_momentum * 0.4) * 10
            
            return max(-1.0, min(1.0, momentum_score))
            
        except Exception:
            return 0.0
    
    def _analyze_volume_pattern(self, volume_data: List[Dict]) -> float:
        """Analyze volume patterns for sentiment."""
        try:
            if len(volume_data) < 10:
                return 0.0
            
            recent_volumes = [float(vol.get('volume', 0)) for vol in volume_data[-10:]]
            
            # Volume trend
            avg_volume = sum(recent_volumes) / len(recent_volumes)
            recent_avg = sum(recent_volumes[-3:]) / 3
            
            volume_trend = (recent_avg - avg_volume) / avg_volume if avg_volume > 0 else 0
            
            # Higher volume usually indicates stronger sentiment
            return max(-0.5, min(0.5, volume_trend))
            
        except Exception:
            return 0.0
    
    def _analyze_volatility(self, price_data: List[Dict]) -> float:
        """Analyze volatility for sentiment (high volatility = uncertainty)."""
        try:
            if len(price_data) < 5:
                return 0.0
            
            recent_closes = [float(candle.get('close', 0)) for candle in price_data[-10:]]
            
            # Calculate price volatility
            price_changes = []
            for i in range(1, len(recent_closes)):
                change = abs(recent_closes[i] - recent_closes[i-1]) / recent_closes[i-1]
                price_changes.append(change)
            
            avg_volatility = sum(price_changes) / len(price_changes) if price_changes else 0
            
            # High volatility reduces sentiment confidence
            # Return negative sentiment for very high volatility
            if avg_volatility > 0.05:  # 5% average change
                return -0.3
            elif avg_volatility < 0.01:  # 1% average change
                return 0.1  # Low volatility is slightly positive
            else:
                return 0.0
                
        except Exception:
            return 0.0
    
    def _neutral_sentiment(self, symbol: str, reason: str) -> SentimentReading:
        """Return neutral sentiment reading."""
        return SentimentReading(
            timestamp=datetime.utcnow(),
            symbol=symbol,
            sentiment=SentimentType.NEUTRAL,
            confidence=0.5,
            score=0.0,
            source="fallback",
            data={"reason": reason}
        )
    
    def get_recent_sentiment(self, symbol: str, hours: int = 24) -> List[SentimentReading]:
        """Get recent sentiment readings for a symbol."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            return [
                reading for reading in self.sentiment_history
                if reading.symbol == symbol and reading.timestamp >= cutoff_time
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting recent sentiment: {e}")
            return []
    
    def get_sentiment_summary(self, symbol: Optional[str] = None) -> Dict:
        """Get sentiment analysis summary."""
        try:
            recent_readings = []
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            for reading in self.sentiment_history:
                if reading.timestamp >= cutoff_time:
                    if symbol is None or reading.symbol == symbol:
                        recent_readings.append(reading)
            
            if not recent_readings:
                return {"status": "No recent sentiment data"}
            
            # Count sentiments
            sentiment_counts = {sentiment.value: 0 for sentiment in SentimentType}
            avg_score = 0.0
            avg_confidence = 0.0
            
            for reading in recent_readings:
                sentiment_counts[reading.sentiment.value] += 1
                avg_score += reading.score
                avg_confidence += reading.confidence
            
            avg_score /= len(recent_readings)
            avg_confidence /= len(recent_readings)
            
            # Determine overall sentiment
            if sentiment_counts["BULLISH"] > sentiment_counts["BEARISH"]:
                overall = "BULLISH"
            elif sentiment_counts["BEARISH"] > sentiment_counts["BULLISH"]:
                overall = "BEARISH"
            else:
                overall = "NEUTRAL"
            
            return {
                "symbol": symbol or "ALL",
                "overall_sentiment": overall,
                "avg_score": avg_score,
                "avg_confidence": avg_confidence,
                "sentiment_counts": sentiment_counts,
                "total_readings": len(recent_readings),
                "period_hours": 24
            }
            
        except Exception as e:
            self.logger.error(f"Error getting sentiment summary: {e}")
            return {"status": "Error calculating summary"}


# Global instance
sentiment_analyzer = MarketSentimentAnalyzer()