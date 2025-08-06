"""
Base classes and interfaces for AI models
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
import numpy as np
import pandas as pd
from datetime import datetime
from enum import Enum

class ModelType(Enum):
    """Supported model types"""
    LSTM = "lstm"
    CNN = "cnn"
    TRANSFORMER = "transformer"
    ENSEMBLE = "ensemble"
    REINFORCEMENT_LEARNING = "rl"

class PredictionType(Enum):
    """Types of predictions"""
    PRICE = "price"
    DIRECTION = "direction"
    VOLATILITY = "volatility"
    PATTERN = "pattern"
    SENTIMENT = "sentiment"

class BaseModel(ABC):
    """Base class for all AI models"""
    
    def __init__(self, model_type: ModelType, name: str, config: Optional[Dict] = None):
        self.model_type = model_type
        self.name = name
        self.config = config or {}
        self.is_trained = False
        self.version = "1.0.0"
        self.created_at = datetime.now()
        self.model = None
        
    @abstractmethod
    def build_model(self) -> Any:
        """Build the model architecture"""
        pass
        
    @abstractmethod
    def train(self, data: pd.DataFrame, **kwargs) -> Dict:
        """Train the model"""
        pass
        
    @abstractmethod
    def predict(self, data: Union[pd.DataFrame, np.ndarray], **kwargs) -> Dict:
        """Make predictions"""
        pass
        
    @abstractmethod
    def evaluate(self, data: pd.DataFrame, targets: np.ndarray) -> Dict:
        """Evaluate model performance"""
        pass
        
    def save_model(self, path: str) -> bool:
        """Save model to disk"""
        try:
            # Implementation will depend on model type
            return True
        except Exception as e:
            print(f"Error saving model: {e}")
            return False
            
    def load_model(self, path: str) -> bool:
        """Load model from disk"""
        try:
            # Implementation will depend on model type
            self.is_trained = True
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False

class PricePredictor(BaseModel):
    """Base class for price prediction models"""
    
    def __init__(self, name: str, sequence_length: int = 60, features: int = 5, config: Optional[Dict] = None):
        super().__init__(ModelType.LSTM, name, config)
        self.sequence_length = sequence_length
        self.features = features
        
    @abstractmethod
    def predict_price(self, market_data: pd.DataFrame, horizon: int = 1) -> Dict:
        """Predict future prices"""
        pass

class PatternDetector(BaseModel):
    """Base class for pattern detection models"""
    
    def __init__(self, name: str, pattern_types: List[str], config: Optional[Dict] = None):
        super().__init__(ModelType.CNN, name, config)
        self.pattern_types = pattern_types
        
    @abstractmethod
    def detect_patterns(self, chart_data: Union[pd.DataFrame, np.ndarray]) -> Dict:
        """Detect chart patterns"""
        pass

class SentimentAnalyzer(BaseModel):
    """Base class for sentiment analysis models"""
    
    def __init__(self, name: str, sources: List[str], config: Optional[Dict] = None):
        super().__init__(ModelType.TRANSFORMER, name, config)
        self.sources = sources
        
    @abstractmethod
    def analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of text"""
        pass
        
    @abstractmethod
    def aggregate_sentiment(self, sentiments: List[Dict]) -> Dict:
        """Aggregate multiple sentiment scores"""
        pass

class TradingAgent(BaseModel):
    """Base class for reinforcement learning trading agents"""
    
    def __init__(self, name: str, action_space: List[str], config: Optional[Dict] = None):
        super().__init__(ModelType.REINFORCEMENT_LEARNING, name, config)
        self.action_space = action_space
        
    @abstractmethod
    def get_action(self, state: np.ndarray) -> Dict:
        """Get trading action for given state"""
        pass
        
    @abstractmethod
    def update_policy(self, experience: Dict) -> Dict:
        """Update policy based on experience"""
        pass

class ModelRegistry:
    """Registry for managing AI models"""
    
    def __init__(self):
        self.models: Dict[str, BaseModel] = {}
        
    def register_model(self, model: BaseModel) -> bool:
        """Register a model"""
        try:
            self.models[model.name] = model
            return True
        except Exception as e:
            print(f"Error registering model {model.name}: {e}")
            return False
            
    def get_model(self, name: str) -> Optional[BaseModel]:
        """Get a registered model"""
        return self.models.get(name)
        
    def list_models(self) -> List[str]:
        """List all registered models"""
        return list(self.models.keys())
        
    def remove_model(self, name: str) -> bool:
        """Remove a model from registry"""
        if name in self.models:
            del self.models[name]
            return True
        return False

# Global model registry instance
model_registry = ModelRegistry()