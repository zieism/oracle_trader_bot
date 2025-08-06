"""
Tests for AI Models and Prediction Engine
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from app.ai.models import LSTMPricePredictor, CNNPatternDetector, MarketTransformer, model_registry
from app.ai.sentiment import AdvancedSentimentAnalyzer, NewsCollector
from app.ai.prediction import PricePredictionEngine
from app.ai.rl import RLTradingAgent


class TestAIModels:
    """Test AI model functionality"""
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        
        # Generate realistic price data
        np.random.seed(42)
        price = 50000  # Starting BTC price
        prices = [price]
        
        for _ in range(99):
            change = np.random.normal(0, 0.02)  # 2% volatility
            price = price * (1 + change)
            prices.append(price)
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.uniform(100, 1000, 100)
        })
        
        # Add technical indicators
        data['rsi'] = np.random.uniform(20, 80, 100)
        data['macd'] = np.random.normal(0, 100, 100)
        data['bb_position'] = np.random.uniform(0, 1, 100)
        
        return data
    
    def test_lstm_predictor_initialization(self):
        """Test LSTM predictor initialization"""
        predictor = LSTMPricePredictor()
        
        assert predictor.name == "lstm_price_predictor"
        assert predictor.sequence_length == 60
        assert predictor.features == 5
        assert not predictor.is_trained
    
    def test_lstm_predictor_build_model(self):
        """Test LSTM model building"""
        predictor = LSTMPricePredictor()
        model_config = predictor.build_model()
        
        assert model_config is not None
        assert model_config['type'] == 'sequential'
        assert len(model_config['layers']) > 0
    
    def test_lstm_predictor_training(self, sample_market_data):
        """Test LSTM predictor training"""
        predictor = LSTMPricePredictor()
        result = predictor.train(sample_market_data)
        
        assert result['status'] == 'success'
        assert predictor.is_trained
        assert 'training_samples' in result
        assert 'validation_samples' in result
    
    def test_lstm_predictor_prediction(self, sample_market_data):
        """Test LSTM price prediction"""
        predictor = LSTMPricePredictor()
        
        # Train first
        predictor.train(sample_market_data)
        
        # Make prediction
        result = predictor.predict_price(sample_market_data, horizon=5)
        
        assert result['status'] == 'success'
        assert 'predicted_price' in result
        assert 'confidence' in result
        assert 'direction' in result
        assert result['direction'] in ['up', 'down']
    
    def test_cnn_pattern_detector_initialization(self):
        """Test CNN pattern detector initialization"""
        detector = CNNPatternDetector()
        
        assert detector.name == "cnn_pattern_detector"
        assert len(detector.pattern_types) > 0
        assert 'head_and_shoulders' in detector.pattern_types
        assert not detector.is_trained
    
    def test_cnn_pattern_detection(self, sample_market_data):
        """Test pattern detection"""
        detector = CNNPatternDetector()
        
        # Train first
        detector.train(sample_market_data)
        
        # Detect patterns
        result = detector.detect_patterns(sample_market_data)
        
        assert result['status'] == 'success'
        assert 'rule_based_patterns' in result
        assert 'peaks' in result
        assert 'valleys' in result
    
    def test_transformer_model_initialization(self):
        """Test transformer model initialization"""
        transformer = MarketTransformer()
        
        assert transformer.name == "market_transformer"
        assert transformer.d_model == 512
        assert transformer.nhead == 8
        assert not transformer.is_trained
    
    def test_transformer_training(self, sample_market_data):
        """Test transformer training"""
        transformer = MarketTransformer()
        result = transformer.train(sample_market_data)
        
        assert result['status'] == 'success'
        assert transformer.is_trained
        assert 'attention_analysis' in result
    
    def test_transformer_prediction(self, sample_market_data):
        """Test transformer sequence prediction"""
        transformer = MarketTransformer()
        
        # Train first
        transformer.train(sample_market_data)
        
        # Make prediction
        result = transformer.predict_sequence(sample_market_data, horizon=10)
        
        assert result['status'] == 'success'
        assert 'market_analysis' in result
        assert 'predictions' in result
        assert len(result['predictions']) == 10


class TestSentimentAnalysis:
    """Test sentiment analysis functionality"""
    
    def test_sentiment_analyzer_initialization(self):
        """Test sentiment analyzer initialization"""
        analyzer = AdvancedSentimentAnalyzer()
        
        assert analyzer.name == "roberta_sentiment"
        assert len(analyzer.sources) > 0
        assert 'news' in analyzer.sources
    
    def test_sentiment_analysis(self):
        """Test sentiment analysis of text"""
        analyzer = AdvancedSentimentAnalyzer()
        
        # Test positive sentiment
        positive_text = "Bitcoin is rallying strongly and showing bullish momentum"
        result = analyzer.analyze_sentiment(positive_text)
        
        assert 'sentiment' in result
        assert 'score' in result
        assert 'confidence' in result
        assert result['sentiment'] in ['positive', 'negative', 'neutral']
    
    def test_sentiment_aggregation(self):
        """Test sentiment aggregation"""
        analyzer = AdvancedSentimentAnalyzer()
        
        sentiments = [
            {'sentiment': 'positive', 'score': 0.8, 'confidence': 0.9},
            {'sentiment': 'positive', 'score': 0.6, 'confidence': 0.7},
            {'sentiment': 'negative', 'score': -0.4, 'confidence': 0.6}
        ]
        
        result = analyzer.aggregate_sentiment(sentiments)
        
        assert 'overall_sentiment' in result
        assert 'overall_score' in result
        assert 'sentiment_distribution' in result
        assert result['total_samples'] == 3
    
    @pytest.mark.asyncio
    async def test_news_collector(self):
        """Test news collection"""
        collector = NewsCollector()
        
        # Test news collection
        articles = await collector.collect_news(['BTC', 'ETH'], max_articles=10)
        
        assert isinstance(articles, list)
        assert len(articles) <= 10
        
        if articles:
            article = articles[0]
            assert hasattr(article, 'title')
            assert hasattr(article, 'content')
            assert hasattr(article, 'source')
            assert hasattr(article, 'relevance_score')


class TestReinforcementLearning:
    """Test reinforcement learning functionality"""
    
    @pytest.fixture
    def sample_trading_data(self):
        """Create sample trading data"""
        dates = pd.date_range(start='2024-01-01', periods=200, freq='1h')
        
        np.random.seed(42)
        price = 50000
        prices = [price]
        
        for _ in range(199):
            change = np.random.normal(0, 0.015)
            price = price * (1 + change)
            prices.append(price)
        
        return pd.DataFrame({
            'timestamp': dates,
            'close': prices,
            'volume': np.random.uniform(100, 1000, 200),
            'rsi': np.random.uniform(20, 80, 200),
            'macd': np.random.normal(0, 100, 200),
            'bb_position': np.random.uniform(0, 1, 200)
        })
    
    def test_rl_agent_initialization(self):
        """Test RL agent initialization"""
        agent = RLTradingAgent()
        
        assert agent.name == "rl_trading_agent_ppo"
        assert agent.algorithm == "PPO"
        assert len(agent.action_space) == 3
        assert not agent.is_trained
    
    def test_rl_agent_training(self, sample_trading_data):
        """Test RL agent training"""
        agent = RLTradingAgent()
        result = agent.train(sample_trading_data, episodes=10)  # Short training for test
        
        assert result['status'] == 'success'
        assert agent.is_trained
        assert 'avg_episode_reward' in result
        assert 'avg_episode_return' in result
    
    def test_rl_agent_action_generation(self, sample_trading_data):
        """Test RL agent action generation"""
        agent = RLTradingAgent()
        
        # Train first
        agent.train(sample_trading_data, episodes=5)
        
        # Generate action
        result = agent.predict(sample_trading_data)
        
        assert result['status'] == 'success'
        assert 'recommended_action' in result
        assert result['recommended_action'] in ['buy', 'sell', 'hold']
        assert 'confidence' in result


class TestPredictionEngine:
    """Test prediction engine functionality"""
    
    @pytest.fixture
    def sample_data(self):
        """Create comprehensive sample data"""
        dates = pd.date_range(start='2024-01-01', periods=150, freq='1h')
        
        np.random.seed(42)
        price = 50000
        prices = []
        volumes = []
        
        for i in range(150):
            # Add some trend and seasonality
            trend = i * 10  # Upward trend
            seasonal = 500 * np.sin(i * 0.1)  # Some seasonality
            noise = np.random.normal(0, 1000)  # Random noise
            
            price = 50000 + trend + seasonal + noise
            prices.append(max(price, 1000))  # Ensure positive prices
            volumes.append(np.random.uniform(100, 2000))
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * 1.02 for p in prices],
            'low': [p * 0.98 for p in prices],
            'close': prices,
            'volume': volumes,
            'rsi': np.random.uniform(20, 80, 150),
            'macd': np.random.normal(0, 100, 150),
            'bb_position': np.random.uniform(0, 1, 150),
            'sma_20': prices,  # Simplified
            'ema_12': prices   # Simplified
        })
        
        return data
    
    def test_prediction_engine_initialization(self):
        """Test prediction engine initialization"""
        engine = PricePredictionEngine()
        
        assert 'lstm' in engine.models
        assert 'transformer' in engine.models
        assert len(engine.ensemble_weights) > 0
    
    def test_prediction_engine_training(self, sample_data):
        """Test prediction engine model training"""
        engine = PricePredictionEngine()
        result = engine.train_models(sample_data)
        
        assert result['status'] == 'success'
        assert 'model_results' in result
        assert 'trained_models' in result
    
    def test_prediction_engine_price_prediction(self, sample_data):
        """Test comprehensive price prediction"""
        engine = PricePredictionEngine()
        
        # Train models first
        engine.train_models(sample_data)
        
        # Make prediction
        result = engine.predict_price('BTC', sample_data, timeframe='1h', horizon=12)
        
        assert result['status'] == 'success'
        assert 'ensemble_price' in result
        assert 'confidence' in result
        assert 'direction' in result
        assert 'confidence_interval' in result
        assert 'uncertainty_metrics' in result
        assert result['symbol'] == 'BTC'
    
    def test_prediction_engine_multiple_timeframes(self, sample_data):
        """Test multiple timeframe predictions"""
        engine = PricePredictionEngine()
        
        # Train models first
        engine.train_models(sample_data)
        
        # Get multi-timeframe predictions
        result = engine.predict_multiple_timeframes('BTC', sample_data)
        
        assert result['status'] == 'success'
        assert 'timeframe_predictions' in result
        assert 'trend_analysis' in result
        
        # Check that we have predictions for different timeframes
        timeframes = result['timeframe_predictions']
        assert len(timeframes) > 0
        
        for tf, pred in timeframes.items():
            assert 'predicted_price' in pred
            assert 'confidence' in pred
            assert 'direction' in pred
    
    def test_model_registry(self):
        """Test model registry functionality"""
        from app.ai.models import model_registry
        
        # Create a test model
        test_model = LSTMPricePredictor()
        
        # Register model
        success = model_registry.register_model(test_model)
        assert success
        
        # Retrieve model
        retrieved_model = model_registry.get_model(test_model.name)
        assert retrieved_model is not None
        assert retrieved_model.name == test_model.name
        
        # List models
        model_names = model_registry.list_models()
        assert test_model.name in model_names


@pytest.mark.integration
class TestIntegrationScenarios:
    """Integration tests for complete AI workflows"""
    
    @pytest.fixture
    def comprehensive_data(self):
        """Create comprehensive test data"""
        dates = pd.date_range(start='2024-01-01', periods=300, freq='1h')
        
        np.random.seed(123)
        base_price = 45000
        prices = []
        
        for i in range(300):
            # More realistic price movement
            returns = np.random.normal(0.0001, 0.02)  # Daily return with volatility
            base_price = base_price * (1 + returns)
            prices.append(base_price)
        
        volumes = np.random.lognormal(5, 1, 300)  # Log-normal volume distribution
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': [p * np.random.uniform(0.995, 1.005) for p in prices],
            'high': [p * np.random.uniform(1.001, 1.02) for p in prices],
            'low': [p * np.random.uniform(0.98, 0.999) for p in prices],
            'close': prices,
            'volume': volumes
        })
        
        # Add technical indicators
        data['rsi'] = np.random.uniform(20, 80, 300)
        data['macd'] = np.random.normal(0, 50, 300)
        data['bb_position'] = np.random.uniform(0, 1, 300)
        data['sma_20'] = data['close'].rolling(20).mean().fillna(data['close'])
        data['ema_12'] = data['close'].ewm(span=12).mean()
        
        return data
    
    def test_complete_ai_workflow(self, comprehensive_data):
        """Test complete AI trading workflow"""
        # Initialize components
        prediction_engine = PricePredictionEngine()
        sentiment_analyzer = AdvancedSentimentAnalyzer()
        rl_agent = RLTradingAgent()
        
        # Train AI models
        pred_result = prediction_engine.train_models(comprehensive_data)
        assert pred_result['status'] == 'success'
        
        rl_result = rl_agent.train(comprehensive_data, episodes=20)
        assert rl_result['status'] == 'success'
        
        # Make predictions
        price_prediction = prediction_engine.predict_price(
            'BTC', comprehensive_data, timeframe='1h', horizon=24
        )
        assert price_prediction['status'] == 'success'
        
        # Analyze sentiment
        test_texts = [
            "Bitcoin shows strong bullish momentum",
            "Market correction expected",
            "Neutral outlook for cryptocurrency"
        ]
        
        sentiment_results = []
        for text in test_texts:
            result = sentiment_analyzer.analyze_sentiment(text)
            sentiment_results.append(result)
        
        aggregated_sentiment = sentiment_analyzer.aggregate_sentiment(sentiment_results)
        assert 'overall_sentiment' in aggregated_sentiment
        
        # Get RL agent recommendation
        agent_recommendation = rl_agent.predict(comprehensive_data)
        assert agent_recommendation['status'] == 'success'
        
        # Verify all components worked together
        assert price_prediction['ensemble_price'] > 0
        assert aggregated_sentiment['total_samples'] == 3
        assert agent_recommendation['recommended_action'] in ['buy', 'sell', 'hold']
        
        print("✓ Complete AI workflow test passed")
        print(f"  - Price prediction: ${price_prediction['ensemble_price']:.2f}")
        print(f"  - Sentiment: {aggregated_sentiment['overall_sentiment']}")
        print(f"  - RL recommendation: {agent_recommendation['recommended_action']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])