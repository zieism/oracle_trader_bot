"""
Price Prediction Engine combining multiple AI models
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from ..models import LSTMPricePredictor, MarketTransformer, model_registry

class PricePredictionEngine:
    """
    Advanced price prediction engine combining multiple AI models
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Model configuration
        self.models = {}
        self.ensemble_weights = self.config.get('ensemble_weights', {
            'lstm': 0.4,
            'transformer': 0.4,
            'ensemble': 0.2
        })
        
        # Prediction parameters
        self.default_horizon = self.config.get('default_horizon', 24)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.7)
        
        # Initialize models
        self._initialize_models()
        
    def _initialize_models(self):
        """Initialize prediction models"""
        try:
            # LSTM Price Predictor
            lstm_config = self.config.get('lstm_config', {
                'sequence_length': 60,
                'features': 5,
                'lstm_units': [50, 50, 50],
                'dropout_rate': 0.2,
                'learning_rate': 0.001
            })
            self.models['lstm'] = LSTMPricePredictor(
                sequence_length=lstm_config['sequence_length'],
                features=lstm_config['features'],
                config=lstm_config
            )
            
            # Transformer Model
            transformer_config = self.config.get('transformer_config', {
                'd_model': 512,
                'nhead': 8,
                'num_layers': 6,
                'sequence_length': 60,
                'prediction_horizon': 10
            })
            self.models['transformer'] = MarketTransformer(
                d_model=transformer_config['d_model'],
                nhead=transformer_config['nhead'],
                num_layers=transformer_config['num_layers'],
                config=transformer_config
            )
            
            # Register models
            for name, model in self.models.items():
                model_registry.register_model(model)
                
        except Exception as e:
            print(f"Error initializing models: {e}")
    
    def train_models(self, data: pd.DataFrame, **kwargs) -> Dict:
        """Train all prediction models"""
        try:
            training_results = {}
            
            for name, model in self.models.items():
                print(f"Training {name} model...")
                result = model.train(data, **kwargs)
                training_results[name] = result
                
                if result.get('status') == 'success':
                    print(f"✓ {name} model trained successfully")
                else:
                    print(f"✗ {name} model training failed: {result.get('message', 'Unknown error')}")
            
            return {
                'status': 'success',
                'model_results': training_results,
                'trained_models': [name for name, result in training_results.items() 
                                 if result.get('status') == 'success']
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def predict_price(self, symbol: str, market_data: pd.DataFrame, 
                     timeframe: str = '1h', horizon: Optional[int] = None) -> Dict:
        """
        Multi-model ensemble price prediction with uncertainty quantification
        """
        try:
            if horizon is None:
                horizon = self.default_horizon
            
            predictions = {}
            confidences = {}
            
            # Get predictions from each model
            for name, model in self.models.items():
                if not model.is_trained:
                    print(f"Warning: {name} model not trained, skipping...")
                    continue
                    
                if name == 'lstm':
                    result = model.predict_price(market_data, horizon=horizon)
                elif name == 'transformer':
                    result = model.predict_sequence(market_data, horizon=horizon)
                else:
                    result = model.predict(market_data, horizon=horizon)
                
                if result.get('status') == 'success':
                    predictions[name] = result
                    confidences[name] = result.get('confidence', result.get('avg_confidence', 0.5))
            
            if not predictions:
                return {
                    'status': 'error',
                    'message': 'No trained models available for prediction'
                }
            
            # Ensemble prediction
            ensemble_result = self._ensemble_predictions(predictions, market_data, symbol, timeframe)
            
            # Add meta-information
            current_price = market_data['close'].iloc[-1] if 'close' in market_data.columns else 0
            
            ensemble_result.update({
                'symbol': symbol,
                'timeframe': timeframe,
                'current_price': current_price,
                'prediction_horizon': horizon,
                'models_used': list(predictions.keys()),
                'individual_predictions': predictions,
                'model_confidences': confidences,
                'prediction_timestamp': datetime.now().isoformat()
            })
            
            return ensemble_result
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _ensemble_predictions(self, predictions: Dict, market_data: pd.DataFrame, 
                            symbol: str, timeframe: str) -> Dict:
        """
        Combine predictions from multiple models using weighted ensemble
        """
        try:
            # Extract price predictions
            price_predictions = []
            weights = []
            confidence_scores = []
            
            for name, result in predictions.items():
                weight = self.ensemble_weights.get(name, 0.33)
                confidence = result.get('confidence', result.get('avg_confidence', 0.5))
                
                # Extract predicted prices
                if 'predicted_price' in result:
                    price_pred = result['predicted_price']
                elif 'predictions' in result and result['predictions']:
                    # For transformer, extract price prediction (first feature)
                    price_pred = result['predictions'][-1] if isinstance(result['predictions'][-1], (int, float)) else result['predictions'][-1][0]
                else:
                    continue
                
                price_predictions.append(price_pred)
                weights.append(weight * confidence)  # Weight by confidence
                confidence_scores.append(confidence)
            
            if not price_predictions:
                return {'status': 'error', 'message': 'No valid price predictions'}
            
            # Normalize weights
            total_weight = sum(weights)
            if total_weight > 0:
                weights = [w / total_weight for w in weights]
            else:
                weights = [1.0 / len(weights)] * len(weights)
            
            # Weighted ensemble prediction
            ensemble_price = sum(p * w for p, w in zip(price_predictions, weights))
            ensemble_confidence = sum(c * w for c, w in zip(confidence_scores, weights))
            
            # Calculate uncertainty metrics
            prediction_variance = np.var(price_predictions)
            prediction_std = np.std(price_predictions)
            
            # Confidence intervals
            confidence_range = prediction_std * 1.96  # 95% confidence interval
            upper_bound = ensemble_price + confidence_range
            lower_bound = ensemble_price - confidence_range
            
            # Direction prediction
            current_price = market_data['close'].iloc[-1]
            direction = 'bullish' if ensemble_price > current_price else 'bearish'
            price_change_pct = ((ensemble_price - current_price) / current_price) * 100
            
            # Risk assessment
            risk_level = 'low'
            if prediction_std / current_price > 0.05:  # >5% standard deviation
                risk_level = 'high'
            elif prediction_std / current_price > 0.02:  # >2% standard deviation
                risk_level = 'medium'
            
            # Support and resistance levels (simplified)
            recent_highs = market_data['high'].tail(20).max() if 'high' in market_data.columns else ensemble_price * 1.05
            recent_lows = market_data['low'].tail(20).min() if 'low' in market_data.columns else ensemble_price * 0.95
            
            return {
                'status': 'success',
                'ensemble_price': float(ensemble_price),
                'confidence': float(ensemble_confidence),
                'direction': direction,
                'price_change_pct': float(price_change_pct),
                'confidence_interval': {
                    'upper': float(upper_bound),
                    'lower': float(lower_bound),
                    'range': float(confidence_range)
                },
                'uncertainty_metrics': {
                    'prediction_variance': float(prediction_variance),
                    'prediction_std': float(prediction_std),
                    'risk_level': risk_level
                },
                'technical_levels': {
                    'resistance': float(recent_highs),
                    'support': float(recent_lows)
                },
                'ensemble_weights': dict(zip(predictions.keys(), weights))
            }
            
        except Exception as e:
            return {'status': 'error', 'message': f'Ensemble error: {str(e)}'}
    
    def get_model_status(self) -> Dict:
        """Get status of all models"""
        try:
            status = {}
            for name, model in self.models.items():
                status[name] = {
                    'is_trained': model.is_trained,
                    'model_type': model.model_type.value,
                    'version': model.version,
                    'created_at': model.created_at.isoformat()
                }
            
            return {
                'status': 'success',
                'models': status,
                'total_models': len(self.models),
                'trained_models': sum(1 for model in self.models.values() if model.is_trained)
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def predict_multiple_timeframes(self, symbol: str, market_data: pd.DataFrame) -> Dict:
        """
        Predict prices for multiple timeframes
        """
        try:
            timeframes = {
                '1h': 1,
                '4h': 4,
                '12h': 12,
                '24h': 24,
                '7d': 168  # 7 days in hours
            }
            
            predictions = {}
            
            for timeframe, horizon in timeframes.items():
                pred_result = self.predict_price(symbol, market_data, timeframe, horizon)
                if pred_result.get('status') == 'success':
                    predictions[timeframe] = {
                        'predicted_price': pred_result['ensemble_price'],
                        'confidence': pred_result['confidence'],
                        'direction': pred_result['direction'],
                        'price_change_pct': pred_result['price_change_pct'],
                        'risk_level': pred_result['uncertainty_metrics']['risk_level']
                    }
            
            # Trend analysis across timeframes
            trend_consistency = self._analyze_trend_consistency(predictions)
            
            return {
                'status': 'success',
                'symbol': symbol,
                'timeframe_predictions': predictions,
                'trend_analysis': trend_consistency,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def _analyze_trend_consistency(self, predictions: Dict) -> Dict:
        """
        Analyze trend consistency across timeframes
        """
        try:
            if not predictions:
                return {'consistency': 'unknown', 'score': 0.0}
            
            directions = [pred['direction'] for pred in predictions.values()]
            bullish_count = directions.count('bullish')
            bearish_count = directions.count('bearish')
            
            total_predictions = len(directions)
            
            if bullish_count >= total_predictions * 0.8:
                consistency = 'strongly_bullish'
                score = bullish_count / total_predictions
            elif bearish_count >= total_predictions * 0.8:
                consistency = 'strongly_bearish'
                score = bearish_count / total_predictions
            elif bullish_count > bearish_count:
                consistency = 'moderately_bullish'
                score = bullish_count / total_predictions
            elif bearish_count > bullish_count:
                consistency = 'moderately_bearish'
                score = bearish_count / total_predictions
            else:
                consistency = 'mixed'
                score = 0.5
            
            # Calculate confidence convergence
            confidences = [pred['confidence'] for pred in predictions.values()]
            avg_confidence = np.mean(confidences)
            confidence_std = np.std(confidences)
            
            return {
                'consistency': consistency,
                'score': float(score),
                'bullish_predictions': bullish_count,
                'bearish_predictions': bearish_count,
                'total_predictions': total_predictions,
                'average_confidence': float(avg_confidence),
                'confidence_stability': float(1.0 / (1.0 + confidence_std))  # Higher is more stable
            }
            
        except Exception as e:
            print(f"Error analyzing trend consistency: {e}")
            return {'consistency': 'unknown', 'score': 0.0}