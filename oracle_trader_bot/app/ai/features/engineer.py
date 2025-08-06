"""
Feature Engineering Pipeline for AI Models
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
from datetime import datetime

class FeatureEngineer:
    """
    Advanced feature engineering for trading AI models
    Generates 100+ engineered features from market data
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Feature configuration
        self.technical_periods = self.config.get('technical_periods', {
            'short': [5, 10, 14, 20],
            'medium': [50, 100],
            'long': [200]
        })
        
        self.volatility_periods = self.config.get('volatility_periods', [10, 20, 30])
        self.momentum_periods = self.config.get('momentum_periods', [5, 10, 20])
    
    def engineer_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate comprehensive feature set from market data
        """
        try:
            # Start with original data
            features = data.copy()
            
            # Basic price features
            features = self._add_price_features(features)
            
            # Technical indicators
            features = self._add_technical_indicators(features)
            
            # Volume features
            features = self._add_volume_features(features)
            
            # Volatility features
            features = self._add_volatility_features(features)
            
            # Momentum features
            features = self._add_momentum_features(features)
            
            # Market microstructure features
            features = self._add_microstructure_features(features)
            
            # Time-based features
            features = self._add_time_features(features)
            
            # Lag features
            features = self._add_lag_features(features)
            
            # Statistical features
            features = self._add_statistical_features(features)
            
            return features
            
        except Exception as e:
            print(f"Error in feature engineering: {e}")
            return data
    
    def _add_price_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add basic price-derived features"""
        if 'close' in data.columns:
            # Price returns
            data['return_1'] = data['close'].pct_change()
            data['return_5'] = data['close'].pct_change(5)
            data['return_20'] = data['close'].pct_change(20)
            
            # Log returns
            data['log_return'] = np.log(data['close'] / data['close'].shift(1))
            
            # Price ratios
            if 'open' in data.columns:
                data['open_close_ratio'] = data['open'] / data['close']
            
            if 'high' in data.columns and 'low' in data.columns:
                data['high_low_ratio'] = data['high'] / data['low']
                data['close_position'] = (data['close'] - data['low']) / (data['high'] - data['low'])
        
        return data
    
    def _add_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicator features"""
        if 'close' in data.columns:
            # Moving averages
            for period in self.technical_periods['short'] + self.technical_periods['medium']:
                data[f'sma_{period}'] = data['close'].rolling(period).mean()
                data[f'ema_{period}'] = data['close'].ewm(span=period).mean()
                data[f'price_sma_{period}_ratio'] = data['close'] / data[f'sma_{period}']
            
            # Bollinger Bands
            for period in [20, 50]:
                sma = data['close'].rolling(period).mean()
                std = data['close'].rolling(period).std()
                data[f'bb_upper_{period}'] = sma + (2 * std)
                data[f'bb_lower_{period}'] = sma - (2 * std)
                data[f'bb_position_{period}'] = (data['close'] - data[f'bb_lower_{period}']) / (data[f'bb_upper_{period}'] - data[f'bb_lower_{period}'])
        
        return data
    
    def _add_volume_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based features"""
        if 'volume' in data.columns:
            # Volume moving averages
            data['volume_sma_20'] = data['volume'].rolling(20).mean()
            data['volume_ratio'] = data['volume'] / data['volume_sma_20']
            
            # Volume price trend
            if 'close' in data.columns:
                data['vpt'] = (data['volume'] * ((data['close'] - data['close'].shift(1)) / data['close'].shift(1))).cumsum()
                
            # On-balance volume
            if 'close' in data.columns:
                obv = []
                obv_val = 0
                for i in range(len(data)):
                    if i == 0:
                        obv.append(0)
                    else:
                        if data['close'].iloc[i] > data['close'].iloc[i-1]:
                            obv_val += data['volume'].iloc[i]
                        elif data['close'].iloc[i] < data['close'].iloc[i-1]:
                            obv_val -= data['volume'].iloc[i]
                        obv.append(obv_val)
                data['obv'] = obv
        
        return data
    
    def _add_volatility_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add volatility-based features"""
        if 'close' in data.columns:
            for period in self.volatility_periods:
                # Price volatility
                data[f'volatility_{period}'] = data['close'].rolling(period).std()
                
                # Return volatility
                returns = data['close'].pct_change()
                data[f'return_volatility_{period}'] = returns.rolling(period).std()
                
                # True Range based volatility
                if 'high' in data.columns and 'low' in data.columns:
                    high_low = data['high'] - data['low']
                    high_close = np.abs(data['high'] - data['close'].shift())
                    low_close = np.abs(data['low'] - data['close'].shift())
                    true_range = np.maximum(high_low, np.maximum(high_close, low_close))
                    data[f'atr_{period}'] = true_range.rolling(period).mean()
        
        return data
    
    def _add_momentum_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add momentum-based features"""
        if 'close' in data.columns:
            for period in self.momentum_periods:
                # Rate of change
                data[f'roc_{period}'] = ((data['close'] - data['close'].shift(period)) / data['close'].shift(period)) * 100
                
                # Momentum
                data[f'momentum_{period}'] = data['close'] - data['close'].shift(period)
        
        return data
    
    def _add_microstructure_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add market microstructure features"""
        if all(col in data.columns for col in ['high', 'low', 'close']):
            # Typical price
            data['typical_price'] = (data['high'] + data['low'] + data['close']) / 3
            
            # Weighted close price
            if 'volume' in data.columns:
                data['weighted_price'] = (data['typical_price'] * data['volume']).rolling(20).sum() / data['volume'].rolling(20).sum()
        
        return data
    
    def _add_time_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add time-based features"""
        if 'timestamp' in data.columns:
            data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
            data['day_of_week'] = pd.to_datetime(data['timestamp']).dt.dayofweek
            data['month'] = pd.to_datetime(data['timestamp']).dt.month
            
            # Cyclic encoding
            data['hour_sin'] = np.sin(2 * np.pi * data['hour'] / 24)
            data['hour_cos'] = np.cos(2 * np.pi * data['hour'] / 24)
            data['day_sin'] = np.sin(2 * np.pi * data['day_of_week'] / 7)
            data['day_cos'] = np.cos(2 * np.pi * data['day_of_week'] / 7)
        
        return data
    
    def _add_lag_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add lagged features"""
        if 'close' in data.columns:
            for lag in [1, 2, 3, 5, 10]:
                data[f'close_lag_{lag}'] = data['close'].shift(lag)
                data[f'return_lag_{lag}'] = data['close'].pct_change().shift(lag)
        
        return data
    
    def _add_statistical_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add statistical features"""
        if 'close' in data.columns:
            # Rolling statistics
            for window in [10, 20, 50]:
                data[f'close_min_{window}'] = data['close'].rolling(window).min()
                data[f'close_max_{window}'] = data['close'].rolling(window).max()
                data[f'close_std_{window}'] = data['close'].rolling(window).std()
                data[f'close_skew_{window}'] = data['close'].rolling(window).skew()
                data[f'close_kurt_{window}'] = data['close'].rolling(window).kurt()
        
        return data
    
    def get_feature_names(self) -> List[str]:
        """Get list of all engineered feature names"""
        # This would return all the feature names generated
        base_features = ['close', 'volume', 'high', 'low', 'open']
        
        engineered_features = []
        
        # Add all the features we generate
        engineered_features.extend(['return_1', 'return_5', 'return_20', 'log_return'])
        
        for period in self.technical_periods['short'] + self.technical_periods['medium']:
            engineered_features.extend([
                f'sma_{period}', f'ema_{period}', f'price_sma_{period}_ratio'
            ])
        
        # Add more feature names as needed
        return base_features + engineered_features