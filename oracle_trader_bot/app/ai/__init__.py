"""
AI Enhancement Module for Oracle Trader Bot

This module provides AI and machine learning capabilities including:
- Deep learning models for price prediction
- Sentiment analysis from news and social media
- Reinforcement learning trading agents
- Pattern recognition and technical analysis
- Smart execution and order routing
"""

from .models import *
from .prediction import *
from .sentiment import *
from .rl import *
from .features import *

__version__ = "1.0.0"

# Export main classes for easy import
__all__ = [
    # Models
    'LSTMPricePredictor',
    'CNNPatternDetector', 
    'MarketTransformer',
    'model_registry',
    
    # Prediction
    'PricePredictionEngine',
    
    # Sentiment
    'AdvancedSentimentAnalyzer',
    'NewsCollector',
    'SentimentResult',
    'NewsArticle',
    
    # Reinforcement Learning
    'RLTradingAgent',
    'TradingEnvironment',
    'TradingAction',
    'ActionType',
    
    # Features
    'FeatureEngineer'
]