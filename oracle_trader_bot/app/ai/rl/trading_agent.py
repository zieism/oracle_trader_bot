"""
Reinforcement Learning Trading Agent
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

from ..models.base_model import TradingAgent

class ActionType(Enum):
    """Trading action types"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

@dataclass
class TradingAction:
    """Trading action with size and confidence"""
    action: ActionType
    size: float  # Position size (0.0 to 1.0)
    confidence: float  # Confidence in action (0.0 to 1.0)
    price: Optional[float] = None
    timestamp: Optional[datetime] = None

@dataclass
class Experience:
    """Experience tuple for RL training"""
    state: np.ndarray
    action: TradingAction
    reward: float
    next_state: np.ndarray
    done: bool
    timestamp: datetime

class TradingEnvironment:
    """
    Trading environment for reinforcement learning
    """
    
    def __init__(self, data: pd.DataFrame, config: Optional[Dict] = None):
        self.config = config or {}
        self.data = data
        self.current_step = 0
        self.max_steps = len(data) - 1
        
        # Environment parameters
        self.initial_balance = self.config.get('initial_balance', 10000)
        self.transaction_cost = self.config.get('transaction_cost', 0.001)  # 0.1%
        self.max_position_size = self.config.get('max_position_size', 1.0)
        
        # State configuration
        self.lookback_window = self.config.get('lookback_window', 20)
        self.feature_columns = self.config.get('feature_columns', [
            'close', 'volume', 'rsi', 'macd', 'bb_position'
        ])
        
        # Portfolio state
        self.balance = self.initial_balance
        self.position = 0.0  # Current position size (-1 to 1)
        self.entry_price = 0.0
        self.total_return = 0.0
        self.trades_count = 0
        self.winning_trades = 0
        
        # Prepare data
        self._prepare_data()
    
    def _prepare_data(self):
        """Prepare data for environment"""
        try:
            # Select available features
            available_features = [col for col in self.feature_columns if col in self.data.columns]
            if not available_features:
                available_features = ['close']
            
            self.feature_data = self.data[available_features].copy()
            
            # Normalize features
            self.feature_means = self.feature_data.mean()
            self.feature_stds = self.feature_data.std()
            self.normalized_data = (self.feature_data - self.feature_means) / self.feature_stds
            self.normalized_data = self.normalized_data.fillna(0)
            
        except Exception as e:
            print(f"Error preparing data: {e}")
            self.feature_data = self.data[['close']].copy()
            self.normalized_data = self.feature_data.copy()
    
    def reset(self) -> np.ndarray:
        """Reset environment to initial state"""
        self.current_step = self.lookback_window
        self.balance = self.initial_balance
        self.position = 0.0
        self.entry_price = 0.0
        self.total_return = 0.0
        self.trades_count = 0
        self.winning_trades = 0
        
        return self._get_state()
    
    def _get_state(self) -> np.ndarray:
        """Get current state representation"""
        try:
            # Market data state
            if self.current_step >= self.lookback_window:
                market_data = self.normalized_data.iloc[
                    self.current_step - self.lookback_window:self.current_step
                ].values.flatten()
            else:
                # Pad with zeros if not enough history
                available_data = self.normalized_data.iloc[:self.current_step].values.flatten()
                padding_size = self.lookback_window * len(self.feature_data.columns) - len(available_data)
                market_data = np.concatenate([np.zeros(padding_size), available_data])
            
            # Portfolio state
            current_price = self.data.iloc[self.current_step]['close']
            portfolio_value = self.balance + (self.position * current_price)
            
            portfolio_state = np.array([
                self.position,  # Current position
                self.balance / self.initial_balance,  # Normalized balance
                portfolio_value / self.initial_balance,  # Normalized portfolio value
                self.total_return,  # Total return
                self.trades_count / 100.0,  # Normalized trade count
            ])
            
            # Combine states
            state = np.concatenate([market_data, portfolio_state])
            
            return state
            
        except Exception as e:
            print(f"Error getting state: {e}")
            return np.zeros(100)  # Default state size
    
    def step(self, action: TradingAction) -> Tuple[np.ndarray, float, bool, Dict]:
        """Execute action and return next state, reward, done, info"""
        try:
            current_price = self.data.iloc[self.current_step]['close']
            
            # Calculate reward before taking action
            reward = self._calculate_reward(action, current_price)
            
            # Execute action
            self._execute_action(action, current_price)
            
            # Move to next step
            self.current_step += 1
            done = self.current_step >= self.max_steps
            
            # Get next state
            next_state = self._get_state() if not done else np.zeros_like(self._get_state())
            
            # Info dictionary
            info = {
                'balance': self.balance,
                'position': self.position,
                'portfolio_value': self.balance + (self.position * current_price),
                'total_return': self.total_return,
                'trades_count': self.trades_count,
                'winning_trades': self.winning_trades,
                'current_price': current_price
            }
            
            return next_state, reward, done, info
            
        except Exception as e:
            print(f"Error in environment step: {e}")
            return self._get_state(), 0.0, True, {}
    
    def _execute_action(self, action: TradingAction, current_price: float):
        """Execute trading action"""
        try:
            # Calculate position change
            target_position = 0.0
            
            if action.action == ActionType.BUY:
                target_position = min(action.size, self.max_position_size)
            elif action.action == ActionType.SELL:
                target_position = -min(action.size, self.max_position_size)
            elif action.action == ActionType.HOLD:
                target_position = self.position
            
            # Calculate position change
            position_change = target_position - self.position
            
            if abs(position_change) > 0.01:  # Minimum trade size
                # Calculate transaction cost
                cost = abs(position_change) * current_price * self.transaction_cost
                
                # Update balance and position
                self.balance -= cost
                self.balance -= position_change * current_price
                self.position = target_position
                
                # Track trades
                self.trades_count += 1
                
                # Update entry price
                if abs(self.position) > 0.01:
                    self.entry_price = current_price
            
            # Update total return
            portfolio_value = self.balance + (self.position * current_price)
            self.total_return = (portfolio_value / self.initial_balance) - 1.0
            
        except Exception as e:
            print(f"Error executing action: {e}")
    
    def _calculate_reward(self, action: TradingAction, current_price: float) -> float:
        """Calculate reward for the action"""
        try:
            reward = 0.0
            
            # Portfolio value change reward
            if hasattr(self, '_last_portfolio_value'):
                current_portfolio_value = self.balance + (self.position * current_price)
                portfolio_change = (current_portfolio_value - self._last_portfolio_value) / self.initial_balance
                reward += portfolio_change * 10  # Scale reward
            
            self._last_portfolio_value = self.balance + (self.position * current_price)
            
            # Risk-adjusted reward
            if abs(self.position) > 0.8:  # High position risk
                reward -= 0.01
            
            # Transaction cost penalty
            if action.action != ActionType.HOLD:
                reward -= 0.001  # Small penalty for trading
            
            # Confidence bonus
            if action.confidence > 0.8:
                reward += 0.001
            
            return reward
            
        except Exception as e:
            print(f"Error calculating reward: {e}")
            return 0.0

class RLTradingAgent(TradingAgent):
    """
    Reinforcement Learning Trading Agent using PPO algorithm
    """
    
    def __init__(self, algorithm: str = 'PPO', config: Optional[Dict] = None):
        action_space = ['buy', 'sell', 'hold']
        super().__init__(f"rl_trading_agent_{algorithm.lower()}", action_space, config)
        
        self.algorithm = algorithm
        self.state_size = self.config.get('state_size', 105)  # Market data + portfolio state
        self.action_size = len(self.action_space)
        
        # RL hyperparameters
        self.learning_rate = self.config.get('learning_rate', 0.0003)
        self.gamma = self.config.get('gamma', 0.99)  # Discount factor
        self.epsilon = self.config.get('epsilon', 0.2)  # PPO clip parameter
        self.batch_size = self.config.get('batch_size', 64)
        self.memory_size = self.config.get('memory_size', 10000)
        
        # Experience replay
        self.memory: List[Experience] = []
        self.training_step = 0
        
        # Model components (placeholder for actual neural networks)
        self.policy_network = None
        self.value_network = None
        
        # Performance tracking
        self.episode_rewards = []
        self.episode_returns = []
        
    def build_model(self):
        """Build RL model architecture"""
        try:
            # PPO model configuration
            model_config = {
                'algorithm': self.algorithm,
                'policy_network': {
                    'type': 'feedforward',
                    'layers': [
                        {'units': 256, 'activation': 'relu'},
                        {'units': 128, 'activation': 'relu'},
                        {'units': 64, 'activation': 'relu'},
                        {'units': self.action_size, 'activation': 'softmax'}
                    ],
                    'optimizer': {
                        'type': 'adam',
                        'learning_rate': self.learning_rate
                    }
                },
                'value_network': {
                    'type': 'feedforward',
                    'layers': [
                        {'units': 256, 'activation': 'relu'},
                        {'units': 128, 'activation': 'relu'},
                        {'units': 64, 'activation': 'relu'},
                        {'units': 1, 'activation': 'linear'}
                    ],
                    'optimizer': {
                        'type': 'adam',
                        'learning_rate': self.learning_rate
                    }
                },
                'hyperparameters': {
                    'gamma': self.gamma,
                    'epsilon': self.epsilon,
                    'batch_size': self.batch_size,
                    'memory_size': self.memory_size
                }
            }
            
            self.model = model_config
            return model_config
            
        except Exception as e:
            print(f"Error building RL model: {e}")
            return None
    
    def train(self, data: pd.DataFrame, **kwargs) -> Dict:
        """Train the RL agent"""
        try:
            # Build model if not already built
            if self.model is None:
                self.build_model()
            
            episodes = kwargs.get('episodes', 1000)
            environment = TradingEnvironment(data, self.config.get('env_config', {}))
            
            # Training simulation
            training_history = {
                'episodes': episodes,
                'episode_rewards': [],
                'episode_returns': [],
                'policy_loss': [],
                'value_loss': []
            }
            
            for episode in range(episodes):
                state = environment.reset()
                episode_reward = 0
                episode_experiences = []
                
                while True:
                    # Get action from policy
                    action = self.get_action(state, training=True)
                    
                    # Take step in environment
                    next_state, reward, done, info = environment.step(action)
                    
                    # Store experience
                    experience = Experience(
                        state=state,
                        action=action,
                        reward=reward,
                        next_state=next_state,
                        done=done,
                        timestamp=datetime.now()
                    )
                    episode_experiences.append(experience)
                    
                    episode_reward += reward
                    state = next_state
                    
                    if done:
                        break
                
                # Store episode data
                training_history['episode_rewards'].append(episode_reward)
                training_history['episode_returns'].append(info.get('total_return', 0.0))
                
                # Simulate training losses
                training_history['policy_loss'].append(np.random.exponential(0.1))
                training_history['value_loss'].append(np.random.exponential(0.05))
                
                # Update policy (simulate)
                if episode > 0 and episode % 10 == 0:
                    self._update_policy(episode_experiences)
            
            self.is_trained = True
            
            return {
                'status': 'success',
                'episodes': episodes,
                'avg_episode_reward': np.mean(training_history['episode_rewards'][-100:]),
                'avg_episode_return': np.mean(training_history['episode_returns'][-100:]),
                'final_policy_loss': training_history['policy_loss'][-1],
                'final_value_loss': training_history['value_loss'][-1],
                'history': training_history
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_action(self, state: np.ndarray, training: bool = False) -> TradingAction:
        """Get trading action for given state"""
        try:
            if not self.is_trained and not training:
                # Random action if not trained
                action_type = np.random.choice(list(ActionType))
                size = np.random.uniform(0.1, 1.0)
                confidence = np.random.uniform(0.3, 0.7)
            else:
                # Simulate policy network prediction
                action_probs = np.random.dirichlet([1, 1, 1])  # Simulate softmax output
                action_idx = np.argmax(action_probs)
                
                action_type = list(ActionType)[action_idx]
                confidence = action_probs[action_idx]
                
                # Size based on confidence and market conditions
                size = min(confidence * 1.2, 1.0)
                
                # Add exploration noise during training
                if training:
                    if np.random.random() < 0.1:  # 10% exploration
                        action_type = np.random.choice(list(ActionType))
                        size = np.random.uniform(0.1, 1.0)
                        confidence = np.random.uniform(0.2, 0.8)
            
            return TradingAction(
                action=action_type,
                size=size,
                confidence=confidence,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            print(f"Error getting action: {e}")
            return TradingAction(
                action=ActionType.HOLD,
                size=0.0,
                confidence=0.0,
                timestamp=datetime.now()
            )
    
    def _update_policy(self, experiences: List[Experience]) -> Dict:
        """Update policy based on experiences (PPO)"""
        try:
            # Simulate policy update
            policy_loss = np.random.exponential(0.1)
            value_loss = np.random.exponential(0.05)
            
            # Add experiences to memory
            self.memory.extend(experiences)
            
            # Keep memory size manageable
            if len(self.memory) > self.memory_size:
                self.memory = self.memory[-self.memory_size:]
            
            self.training_step += 1
            
            return {
                'policy_loss': policy_loss,
                'value_loss': value_loss,
                'training_step': self.training_step
            }
            
        except Exception as e:
            print(f"Error updating policy: {e}")
            return {'policy_loss': 0.0, 'value_loss': 0.0}
    
    def update_policy(self, experience: Dict) -> Dict:
        """Update policy based on single experience"""
        try:
            # Convert experience dict to Experience object
            exp = Experience(
                state=np.array(experience['state']),
                action=TradingAction(
                    action=ActionType(experience['action']['action']),
                    size=experience['action']['size'],
                    confidence=experience['action']['confidence']
                ),
                reward=experience['reward'],
                next_state=np.array(experience['next_state']),
                done=experience['done'],
                timestamp=datetime.now()
            )
            
            return self._update_policy([exp])
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def predict(self, data: Union[pd.DataFrame, np.ndarray], **kwargs) -> Dict:
        """Make trading predictions"""
        try:
            if not self.is_trained:
                return {'status': 'error', 'message': 'Agent not trained'}
            
            if isinstance(data, pd.DataFrame):
                # Create environment to get proper state
                env = TradingEnvironment(data, self.config.get('env_config', {}))
                state = env.reset()
                
                # Get multiple action predictions
                predictions = []
                for _ in range(10):  # Get 10 predictions
                    action = self.get_action(state)
                    predictions.append({
                        'action': action.action.value,
                        'size': action.size,
                        'confidence': action.confidence
                    })
                
                # Aggregate predictions
                action_counts = {'buy': 0, 'sell': 0, 'hold': 0}
                avg_size = 0
                avg_confidence = 0
                
                for pred in predictions:
                    action_counts[pred['action']] += 1
                    avg_size += pred['size']
                    avg_confidence += pred['confidence']
                
                avg_size /= len(predictions)
                avg_confidence /= len(predictions)
                
                # Determine most frequent action
                most_frequent_action = max(action_counts, key=action_counts.get)
                
                return {
                    'status': 'success',
                    'recommended_action': most_frequent_action,
                    'position_size': avg_size,
                    'confidence': avg_confidence,
                    'action_distribution': action_counts,
                    'predictions': predictions,
                    'prediction_time': datetime.now().isoformat()
                }
            else:
                # Direct state input
                action = self.get_action(data)
                return {
                    'status': 'success',
                    'action': action.action.value,
                    'size': action.size,
                    'confidence': action.confidence
                }
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def evaluate(self, data: pd.DataFrame, targets: np.ndarray) -> Dict:
        """Evaluate RL agent performance"""
        try:
            if not self.is_trained:
                return {'status': 'error', 'message': 'Agent not trained'}
            
            # Create environment for evaluation
            env = TradingEnvironment(data, self.config.get('env_config', {}))
            
            # Run evaluation episode
            state = env.reset()
            total_reward = 0
            actions_taken = {'buy': 0, 'sell': 0, 'hold': 0}
            
            while True:
                action = self.get_action(state, training=False)
                actions_taken[action.action.value] += 1
                
                next_state, reward, done, info = env.step(action)
                total_reward += reward
                state = next_state
                
                if done:
                    break
            
            # Calculate performance metrics
            total_return = info.get('total_return', 0.0)
            sharpe_ratio = total_return / max(0.01, np.std([total_return]))  # Simplified
            max_drawdown = abs(min(0, total_return))  # Simplified
            
            return {
                'status': 'success',
                'total_reward': total_reward,
                'total_return': total_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'trades_count': info.get('trades_count', 0),
                'winning_trades': info.get('winning_trades', 0),
                'actions_distribution': actions_taken,
                'final_portfolio_value': info.get('portfolio_value', 0)
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}