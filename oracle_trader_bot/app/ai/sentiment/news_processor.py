"""
News data collection and processing for sentiment analysis
"""

import asyncio
import aiohttp
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, AsyncIterator
from datetime import datetime, timedelta
import json
import time
from dataclasses import dataclass

@dataclass
class NewsArticle:
    """News article data structure"""
    title: str
    content: str
    source: str
    published_at: datetime
    url: str
    symbols: List[str]
    relevance_score: float = 0.0
    sentiment_score: Optional[float] = None

class NewsCollector:
    """
    News data collector for market sentiment analysis
    Integrates with multiple news APIs and RSS feeds
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # API configurations
        self.alpha_vantage_key = self.config.get('alpha_vantage_key', 'demo')
        self.news_api_key = self.config.get('news_api_key', 'demo')
        self.finnhub_key = self.config.get('finnhub_key', 'demo')
        
        # News sources configuration
        self.sources = self.config.get('sources', [
            'alpha_vantage',
            'newsapi',
            'finnhub',
            'coindesk',
            'cointelegraph'
        ])
        
        # Rate limiting
        self.rate_limits = {
            'alpha_vantage': {'calls_per_minute': 5, 'last_call': 0},
            'newsapi': {'calls_per_minute': 60, 'last_call': 0},
            'finnhub': {'calls_per_minute': 30, 'last_call': 0}
        }
        
        # Crypto and stock symbols to track
        self.tracked_symbols = self.config.get('symbols', [
            'BTC', 'ETH', 'ADA', 'SOL', 'MATIC', 'AVAX',
            'AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'
        ])
        
        # Relevance keywords for filtering
        self.relevance_keywords = {
            'crypto': [
                'bitcoin', 'ethereum', 'cryptocurrency', 'crypto', 'blockchain',
                'defi', 'nft', 'altcoin', 'hodl', 'mining', 'staking'
            ],
            'finance': [
                'stock', 'market', 'trading', 'investment', 'portfolio',
                'earnings', 'revenue', 'profit', 'dividend', 'ipo'
            ],
            'economic': [
                'inflation', 'fed', 'interest rate', 'gdp', 'unemployment',
                'recession', 'economy', 'monetary policy'
            ]
        }
    
    async def check_rate_limit(self, source: str) -> bool:
        """
        Check if we can make an API call based on rate limits
        """
        try:
            current_time = time.time()
            rate_limit = self.rate_limits.get(source, {'calls_per_minute': 60, 'last_call': 0})
            
            time_since_last = current_time - rate_limit['last_call']
            min_interval = 60 / rate_limit['calls_per_minute']
            
            if time_since_last >= min_interval:
                self.rate_limits[source]['last_call'] = current_time
                return True
            
            return False
            
        except Exception as e:
            print(f"Error checking rate limit: {e}")
            return False
    
    def calculate_relevance_score(self, title: str, content: str, symbols: List[str]) -> float:
        """
        Calculate relevance score for a news article
        """
        try:
            score = 0.0
            text = (title + " " + content).lower()
            
            # Check for tracked symbols
            for symbol in symbols:
                if symbol.lower() in text:
                    score += 0.3
            
            # Check for relevance keywords
            for category, keywords in self.relevance_keywords.items():
                category_score = 0
                for keyword in keywords:
                    if keyword in text:
                        category_score += 1
                
                # Normalize and add to total score
                score += min(category_score / len(keywords), 0.4)
            
            # Boost score for title mentions
            title_lower = title.lower()
            for symbol in symbols:
                if symbol.lower() in title_lower:
                    score += 0.2
            
            return min(score, 1.0)
            
        except Exception as e:
            print(f"Error calculating relevance score: {e}")
            return 0.0
    
    async def collect_alpha_vantage_news(self, symbols: List[str]) -> List[NewsArticle]:
        """
        Collect news from Alpha Vantage API
        """
        articles = []
        
        try:
            if not await self.check_rate_limit('alpha_vantage'):
                return articles
            
            # Simulate Alpha Vantage news data
            for i in range(np.random.randint(3, 8)):
                article = NewsArticle(
                    title=f"Market Analysis: {np.random.choice(symbols)} Shows Strong Movement",
                    content=f"Detailed analysis of recent price action in {np.random.choice(symbols)}. Technical indicators suggest continued volatility in the coming weeks.",
                    source="alpha_vantage",
                    published_at=datetime.now() - timedelta(hours=np.random.randint(1, 24)),
                    url=f"https://alphavantage.co/news/{i}",
                    symbols=[np.random.choice(symbols)],
                    relevance_score=np.random.uniform(0.6, 0.9)
                )
                articles.append(article)
            
        except Exception as e:
            print(f"Error collecting Alpha Vantage news: {e}")
        
        return articles
    
    async def collect_newsapi_news(self, symbols: List[str]) -> List[NewsArticle]:
        """
        Collect news from NewsAPI
        """
        articles = []
        
        try:
            if not await self.check_rate_limit('newsapi'):
                return articles
            
            # Simulate NewsAPI data
            for i in range(np.random.randint(5, 12)):
                symbol = np.random.choice(symbols)
                article = NewsArticle(
                    title=f"Breaking: {symbol} Reaches New Price Levels",
                    content=f"Recent developments in {symbol} market show significant investor interest. Trading volume has increased substantially.",
                    source="newsapi",
                    published_at=datetime.now() - timedelta(hours=np.random.randint(1, 48)),
                    url=f"https://newsapi.org/article/{i}",
                    symbols=[symbol],
                    relevance_score=np.random.uniform(0.5, 0.85)
                )
                articles.append(article)
            
        except Exception as e:
            print(f"Error collecting NewsAPI news: {e}")
        
        return articles
    
    async def collect_finnhub_news(self, symbols: List[str]) -> List[NewsArticle]:
        """
        Collect news from Finnhub API
        """
        articles = []
        
        try:
            if not await self.check_rate_limit('finnhub'):
                return articles
            
            # Simulate Finnhub news data
            for i in range(np.random.randint(4, 10)):
                symbol = np.random.choice(symbols)
                article = NewsArticle(
                    title=f"Financial Report: {symbol} Market Update",
                    content=f"Comprehensive market analysis for {symbol} including technical and fundamental perspectives. Key resistance and support levels identified.",
                    source="finnhub",
                    published_at=datetime.now() - timedelta(hours=np.random.randint(1, 36)),
                    url=f"https://finnhub.io/news/{i}",
                    symbols=[symbol],
                    relevance_score=np.random.uniform(0.7, 0.95)
                )
                articles.append(article)
            
        except Exception as e:
            print(f"Error collecting Finnhub news: {e}")
        
        return articles
    
    async def collect_crypto_news(self, symbols: List[str]) -> List[NewsArticle]:
        """
        Collect cryptocurrency-specific news
        """
        articles = []
        
        try:
            # Simulate crypto news sources
            crypto_sources = ['coindesk', 'cointelegraph', 'cryptonews']
            
            for source in crypto_sources:
                for i in range(np.random.randint(2, 6)):
                    symbol = np.random.choice([s for s in symbols if s in ['BTC', 'ETH', 'ADA', 'SOL']])
                    article = NewsArticle(
                        title=f"Crypto Update: {symbol} Shows Market Leadership",
                        content=f"Latest developments in {symbol} ecosystem demonstrate strong fundamentals and growing adoption across various sectors.",
                        source=source,
                        published_at=datetime.now() - timedelta(hours=np.random.randint(1, 24)),
                        url=f"https://{source}.com/news/{i}",
                        symbols=[symbol],
                        relevance_score=np.random.uniform(0.8, 0.95)
                    )
                    articles.append(article)
            
        except Exception as e:
            print(f"Error collecting crypto news: {e}")
        
        return articles
    
    async def collect_news(self, symbols: Optional[List[str]] = None, max_articles: int = 50) -> List[NewsArticle]:
        """
        Collect news from all configured sources
        """
        try:
            if symbols is None:
                symbols = self.tracked_symbols
            
            all_articles = []
            
            # Collect from each source
            tasks = []
            
            if 'alpha_vantage' in self.sources:
                tasks.append(self.collect_alpha_vantage_news(symbols))
            
            if 'newsapi' in self.sources:
                tasks.append(self.collect_newsapi_news(symbols))
            
            if 'finnhub' in self.sources:
                tasks.append(self.collect_finnhub_news(symbols))
            
            # Collect crypto-specific news
            crypto_symbols = [s for s in symbols if s in ['BTC', 'ETH', 'ADA', 'SOL', 'MATIC', 'AVAX']]
            if crypto_symbols:
                tasks.append(self.collect_crypto_news(crypto_symbols))
            
            # Execute all collection tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            for result in results:
                if isinstance(result, list):
                    all_articles.extend(result)
                elif isinstance(result, Exception):
                    print(f"Error in news collection: {result}")
            
            # Sort by relevance score and published time
            all_articles.sort(key=lambda x: (x.relevance_score, x.published_at), reverse=True)
            
            # Limit number of articles
            return all_articles[:max_articles]
            
        except Exception as e:
            print(f"Error collecting news: {e}")
            return []
    
    def filter_articles(self, articles: List[NewsArticle], 
                       min_relevance: float = 0.5,
                       hours_back: int = 24,
                       symbols: Optional[List[str]] = None) -> List[NewsArticle]:
        """
        Filter articles based on relevance, time, and symbols
        """
        try:
            filtered = []
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            for article in articles:
                # Check relevance threshold
                if article.relevance_score < min_relevance:
                    continue
                
                # Check time window
                if article.published_at < cutoff_time:
                    continue
                
                # Check symbols if specified
                if symbols:
                    if not any(symbol in article.symbols for symbol in symbols):
                        continue
                
                filtered.append(article)
            
            return filtered
            
        except Exception as e:
            print(f"Error filtering articles: {e}")
            return articles
    
    def to_dataframe(self, articles: List[NewsArticle]) -> pd.DataFrame:
        """
        Convert news articles to pandas DataFrame
        """
        try:
            data = []
            for article in articles:
                data.append({
                    'title': article.title,
                    'content': article.content,
                    'source': article.source,
                    'published_at': article.published_at,
                    'url': article.url,
                    'symbols': ','.join(article.symbols),
                    'relevance_score': article.relevance_score,
                    'sentiment_score': article.sentiment_score
                })
            
            return pd.DataFrame(data)
            
        except Exception as e:
            print(f"Error converting to DataFrame: {e}")
            return pd.DataFrame()
    
    async def get_latest_news_sentiment(self, symbols: List[str], hours_back: int = 6) -> Dict:
        """
        Get latest news and basic sentiment analysis
        """
        try:
            # Collect recent news
            articles = await self.collect_news(symbols)
            
            # Filter for recent and relevant articles
            filtered_articles = self.filter_articles(
                articles, 
                min_relevance=0.6,
                hours_back=hours_back,
                symbols=symbols
            )
            
            # Basic sentiment analysis on titles
            sentiment_summary = {
                'positive': 0,
                'negative': 0,
                'neutral': 0,
                'total_articles': len(filtered_articles)
            }
            
            positive_words = ['bullish', 'rally', 'surge', 'gain', 'profit', 'up', 'rise']
            negative_words = ['bearish', 'crash', 'fall', 'drop', 'loss', 'down', 'decline']
            
            for article in filtered_articles:
                title_lower = article.title.lower()
                
                positive_count = sum(1 for word in positive_words if word in title_lower)
                negative_count = sum(1 for word in negative_words if word in title_lower)
                
                if positive_count > negative_count:
                    sentiment_summary['positive'] += 1
                elif negative_count > positive_count:
                    sentiment_summary['negative'] += 1
                else:
                    sentiment_summary['neutral'] += 1
            
            # Calculate sentiment percentages
            total = sentiment_summary['total_articles']
            if total > 0:
                sentiment_summary.update({
                    'positive_pct': sentiment_summary['positive'] / total,
                    'negative_pct': sentiment_summary['negative'] / total,
                    'neutral_pct': sentiment_summary['neutral'] / total
                })
            else:
                sentiment_summary.update({
                    'positive_pct': 0.0,
                    'negative_pct': 0.0,
                    'neutral_pct': 0.0
                })
            
            return {
                'status': 'success',
                'articles': [
                    {
                        'title': article.title,
                        'source': article.source,
                        'published_at': article.published_at.isoformat(),
                        'relevance_score': article.relevance_score,
                        'symbols': article.symbols
                    }
                    for article in filtered_articles[:10]  # Top 10 articles
                ],
                'sentiment_summary': sentiment_summary,
                'collection_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'sentiment_summary': {
                    'positive': 0, 'negative': 0, 'neutral': 0,
                    'total_articles': 0, 'positive_pct': 0.0,
                    'negative_pct': 0.0, 'neutral_pct': 0.0
                }
            }