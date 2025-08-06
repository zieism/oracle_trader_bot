"""
Sentiment Analysis Package
"""

from .analyzer import AdvancedSentimentAnalyzer, SentimentResult
from .news_processor import NewsCollector, NewsArticle

__all__ = [
    'AdvancedSentimentAnalyzer',
    'SentimentResult', 
    'NewsCollector',
    'NewsArticle'
]