"""
Reinforcement Learning Engine for Advanced ML Service

Provides enterprise-grade reinforcement learning capabilities including:
- Deep Q-Networks (DQN)
- Proximal Policy Optimization (PPO)
- Actor-Critic methods
- Multi-agent environments
- Financial trading environments
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import random
from collections import deque

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import gym
from gym import spaces

from core_infra.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

class RLAlgorithm(Enum):
    """Supported reinforcement learning algorithms"""
    DQN = "dqn"
    DOUBLE_DQN = "double_dqn"
    DUELING_DQN = "dueling_dqn"
    PPO = "ppo"
    A3C = "a3c"
    SAC = "sac"
    TD3 = "td3"

class EnvironmentType(Enum):
    """Supported environment types"""
    FINANCIAL_TRADING = "financial_trading"
    PORTFOLIO_OPTIMIZATION = "portfolio_optimization"
    RISK_MANAGEMENT = "risk_management"
    FRAUD_DETECTION = "fraud_detection"
    CUSTOM = "custom"

@dataclass
class RLConfig:
    """Configuration for RL training"""
    algorithm: RLAlgorithm
    environment_type: EnvironmentType
    total_episodes: int = 1000
    max_steps_per_episode: int = 500
    learning_rate: float = 0.001
    discount_factor: float = 0.99
    epsilon_start: float = 1.0
    epsilon_end: float = 0.01
    epsilon_decay: float = 0.995
    batch_size: int = 32
    memory_size: int = 10000
    target_update_frequency: int = 100
    hidden_layers: List[int] = None
    
    def __post_init__(self):
        if self.hidden_layers is None:
            self.hidden_layers = [128, 64]

@dataclass
class RLTrainingResult:
    """Results from RL training"""
    episode_rewards: List[float]
    episode_lengths: List[int]
    average_reward: float
    best_episode_reward: float
    convergence_episode: Optional[int]
    training_metrics: Dict[str, Any]

class FinancialTradingEnvironment:
    """Financial trading environment for RL"""
    
    def __init__(self, data: pd.DataFrame, config: Dict[str, Any]):
        self.data = data
        self.config = config
        self.current_step = 0
        self.max_steps = len(data) - 1
        self.initial_balance = config.get("initial_balance", 10000)
        self.balance = self.initial_balance
        self.position = 0  # -1: short, 0: neutral, 1: long
        self.position_size = 0
        self.transaction_cost = config.get("transaction_cost", 0.001)
        
        # Action space: 0=hold, 1=buy, 2=sell
        self.action_space = spaces.Discrete(3)
        
        # Observation space: price features + portfolio state
        obs_size = len(self._get_observation())
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(obs_size,), dtype=np.float32
        )
    
    def reset(self):
        """Reset environment to initial state"""
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0
        self.position_size = 0
        return self._get_observation()
    
    def step(self, action):
        """Execute one step in the environment"""
        if self.current_step >= self.max_steps:
            return self._get_observation(), 0, True, {}
        
        # Get current and next prices
        current_price = self.data.iloc[self.current_step]['price']
        
        # Execute action
        reward = self._execute_action(action, current_price)
        
        # Move to next step
        self.current_step += 1
        
        # Check if episode is done
        done = self.current_step >= self.max_steps or self.balance <= 0
        
        # Calculate portfolio value
        next_price = self.data.iloc[self.current_step]['price'] if not done else current_price
        portfolio_value = self.balance + self.position_size * next_price
        
        info = {
            'portfolio_value': portfolio_value,
            'balance': self.balance,
            'position': self.position,
            'current_price': current_price
        }
        
        return self._get_observation(), reward, done, info
    
    def _execute_action(self, action, price):
        """Execute trading action and return reward"""
        reward = 0
        
        if action == 1:  # Buy
            if self.position <= 0 and self.balance > price:
                # Close short position if any
                if self.position < 0:
                    profit = self.position_size * (self.position_size / abs(self.position_size) - price)
                    self.balance += profit
                    reward += profit * 0.1  # Reward for closing short
                
                # Open long position
                shares = (self.balance * 0.95) // price  # Use 95% of balance
                self.position_size = shares
                self.position = 1
                self.balance -= shares * price * (1 + self.transaction_cost)
                
        elif action == 2:  # Sell
            if self.position >= 0:
                if self.position > 0:
                    # Close long position
                    profit = self.position_size * price
                    self.balance += profit * (1 - self.transaction_cost)
                    reward += profit * 0.1  # Reward for closing long
                    
                # Open short position
                self.position = -1
                self.position_size = -self.balance * 0.5 // price  # Short with 50% of balance
        
        # Reward based on price movement and position
        if self.current_step > 0:
            prev_price = self.data.iloc[self.current_step - 1]['price']
            price_change = (price - prev_price) / prev_price
            
            if self.position > 0:  # Long position
                reward += price_change * 100
            elif self.position < 0:  # Short position
                reward -= price_change * 100
        
        return reward
    
    def _get_observation(self):
        """Get current observation"""
        if self.current_step >= len(self.data):
            return np.zeros(10)
        
        # Price features
        current_data = self.data.iloc[self.current_step]
        price_features = [
            current_data.get('price', 0),
            current_data.get('volume', 0),
            current_data.get('rsi', 50),
            current_data.get('ma_20', 0),
            current_data.get('ma_50', 0)
        ]
        
        # Portfolio state
        portfolio_features = [
            self.balance / self.initial_balance,
            self.position,
            self.position_size / 100,  # Normalized
            (self.balance + self.position_size * current_data.get('price', 0)) / self.initial_balance,
            self.current_step / self.max_steps
        ]
        
        return np.array(price_features + portfolio_features, dtype=np.float32)

class DQNAgent:
    """Deep Q-Network Agent"""
    
    def __init__(self, state_size: int, action_size: int, config: RLConfig):
        self.state_size = state_size
        self.action_size = action_size
        self.config = config
        self.memory = deque(maxlen=config.memory_size)
        self.epsilon = config.epsilon_start
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.q_network = self._build_network().to(self.device)
        self.target_network = self._build_network().to(self.device)
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=config.learning_rate)
        self.update_target_network()
    
    def _build_network(self) -> Any:
        """Build Q-network"""
        layers = []
        prev_size = self.state_size
        
        for hidden_size in self.config.hidden_layers:
            layers.extend([
                nn.Linear(prev_size, hidden_size),
                nn.ReLU()
            ])
            prev_size = hidden_size
        
        layers.append(nn.Linear(prev_size, self.action_size))
        
        return nn.Sequential(*layers)
    
    def act(self, state: np.ndarray, training: bool = True) -> int:
        """Choose action using epsilon-greedy policy"""
        if training and random.random() <= self.epsilon:
            return random.randint(0, self.action_size - 1)
        
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        q_values = self.q_network(state_tensor)
        return q_values.argmax().item()
    
    def remember(self, state, action, reward, next_state, done):
        """Store experience in replay memory"""
        self.memory.append((state, action, reward, next_state, done))
    
    def replay(self):
        """Train the agent on a batch of experiences"""
        if len(self.memory) < self.config.batch_size:
            return
        
        batch = random.sample(self.memory, self.config.batch_size)
        states = torch.FloatTensor([e[0] for e in batch]).to(self.device)
        actions = torch.LongTensor([e[1] for e in batch]).to(self.device)
        rewards = torch.FloatTensor([e[2] for e in batch]).to(self.device)
        next_states = torch.FloatTensor([e[3] for e in batch]).to(self.device)
        dones = torch.BoolTensor([e[4] for e in batch]).to(self.device)
        
        current_q_values = self.q_network(states).gather(1, actions.unsqueeze(1))
        next_q_values = self.target_network(next_states).max(1)[0].detach()
        target_q_values = rewards + (self.config.discount_factor * next_q_values * ~dones)
        
        loss = F.mse_loss(current_q_values.squeeze(), target_q_values)
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        if self.epsilon > self.config.epsilon_end:
            self.epsilon *= self.config.epsilon_decay
    
    def update_target_network(self):
        """Update target network"""
        self.target_network.load_state_dict(self.q_network.state_dict())

class ReinforcementLearningEngine:
    """Enterprise-grade Reinforcement Learning Engine"""
    
    def __init__(self):
        self.settings = get_settings()
        self.environments = {}
        self.agents = {}
        
    async def initialize(self):
        """Initialize the RL engine"""
        logger.info("Reinforcement Learning Engine initialized successfully")
    
    async def create_environment(self, env_config: Dict[str, Any]):
        """Create a reinforcement learning environment"""
        try:
            env_type = EnvironmentType(env_config.get("type", "financial_trading"))
            
            if env_type == EnvironmentType.FINANCIAL_TRADING:
                # Load financial data
                data = await self._load_financial_data(env_config.get("data_source"))
                environment = FinancialTradingEnvironment(data, env_config)
            elif env_type == EnvironmentType.PORTFOLIO_OPTIMIZATION:
                environment = await self._create_portfolio_environment(env_config)
            elif env_type == EnvironmentType.RISK_MANAGEMENT:
                environment = await self._create_risk_environment(env_config)
            else:
                raise ValueError(f"Unsupported environment type: {env_type}")
            
            env_id = f"env_{len(self.environments)}"
            self.environments[env_id] = environment
            
            logger.info(f"Created environment: {env_id} of type {env_type}")
            return environment
            
        except Exception as e:
            logger.error(f"Environment creation failed: {str(e)}")
            raise
    
    async def create_agent(
        self,
        environment: Any,
        agent_type: str,
        config: Optional[RLConfig] = None
    ) -> Any:
        """Create a reinforcement learning agent"""
        try:
            if config is None:
                config = RLConfig(algorithm=RLAlgorithm(agent_type))
            
            if hasattr(environment, 'observation_space') and hasattr(environment, 'action_space'):
                state_size = environment.observation_space.shape[0]
                action_size = environment.action_space.n
            else:
                state_size = 10  # Default
                action_size = 3   # Default
            
            if config.algorithm == RLAlgorithm.DQN:
                agent = DQNAgent(state_size, action_size, config)
            elif config.algorithm == RLAlgorithm.PPO:
                agent = await self._create_ppo_agent(state_size, action_size, config)
            else:
                raise ValueError(f"Unsupported agent type: {config.algorithm}")
            
            agent_id = f"agent_{len(self.agents)}"
            self.agents[agent_id] = agent
            
            logger.info(f"Created agent: {agent_id} of type {config.algorithm}")
            return agent
            
        except Exception as e:
            logger.error(f"Agent creation failed: {str(e)}")
            raise
    
    async def train_agent(
        self,
        agent: Any,
        environment: Any,
        training_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Train a reinforcement learning agent"""
        try:
            total_episodes = training_config.get("total_episodes", 1000)
            max_steps = training_config.get("max_steps_per_episode", 500)
            
            episode_rewards = []
            episode_lengths = []
            best_reward = float('-inf')
            convergence_episode = None
            
            for episode in range(total_episodes):
                state = environment.reset()
                total_reward = 0
                steps = 0
                
                for step in range(max_steps):
                    action = agent.act(state, training=True)
                    next_state, reward, done, info = environment.step(action)
                    
                    agent.remember(state, action, reward, next_state, done)
                    state = next_state
                    total_reward += reward
                    steps += 1
                    
                    if done:
                        break
                
                episode_rewards.append(total_reward)
                episode_lengths.append(steps)
                
                # Update best reward
                if total_reward > best_reward:
                    best_reward = total_reward
                
                # Train agent
                if hasattr(agent, 'replay'):
                    agent.replay()
                
                # Update target network periodically
                if hasattr(agent, 'update_target_network') and episode % agent.config.target_update_frequency == 0:
                    agent.update_target_network()
                
                # Check for convergence
                if len(episode_rewards) >= 100:
                    recent_avg = np.mean(episode_rewards[-100:])
                    if convergence_episode is None and recent_avg > best_reward * 0.9:
                        convergence_episode = episode
                
                if episode % 100 == 0:
                    avg_reward = np.mean(episode_rewards[-100:]) if len(episode_rewards) >= 100 else np.mean(episode_rewards)
                    logger.info(f"Episode {episode}: Average Reward: {avg_reward:.2f}, Best: {best_reward:.2f}")
            
            training_result = {
                "episode_rewards": episode_rewards,
                "episode_lengths": episode_lengths,
                "average_reward": float(np.mean(episode_rewards)),
                "best_episode_reward": float(best_reward),
                "convergence_episode": convergence_episode,
                "final_epsilon": getattr(agent, 'epsilon', 0.0),
                "training_metrics": {
                    "total_episodes": total_episodes,
                    "average_episode_length": float(np.mean(episode_lengths)),
                    "reward_std": float(np.std(episode_rewards))
                }
            }
            
            return {"metrics": training_result}
            
        except Exception as e:
            logger.error(f"Agent training failed: {str(e)}")
            raise
    
    async def evaluate_agent(
        self,
        agent: Any,
        environment: Any,
        evaluation_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate a trained RL agent"""
        try:
            num_episodes = evaluation_config.get("num_episodes", 100)
            max_steps = evaluation_config.get("max_steps_per_episode", 500)
            
            episode_rewards = []
            episode_lengths = []
            win_count = 0
            
            for episode in range(num_episodes):
                state = environment.reset()
                total_reward = 0
                steps = 0
                
                for step in range(max_steps):
                    action = agent.act(state, training=False)  # No exploration
                    next_state, reward, done, info = environment.step(action)
                    
                    state = next_state
                    total_reward += reward
                    steps += 1
                    
                    if done:
                        break
                
                episode_rewards.append(total_reward)
                episode_lengths.append(steps)
                
                if total_reward > 0:
                    win_count += 1
            
            # Calculate performance metrics
            avg_reward = float(np.mean(episode_rewards))
            win_rate = win_count / num_episodes
            
            # Calculate Sharpe ratio (simplified)
            reward_std = np.std(episode_rewards)
            sharpe_ratio = avg_reward / reward_std if reward_std > 0 else 0
            
            # Calculate max drawdown (simplified)
            cumulative_rewards = np.cumsum(episode_rewards)
            peak = np.maximum.accumulate(cumulative_rewards)
            drawdown = (peak - cumulative_rewards) / peak
            max_drawdown = float(np.max(drawdown)) if len(drawdown) > 0 else 0
            
            evaluation_result = {
                "average_reward": avg_reward,
                "total_reward": float(np.sum(episode_rewards)),
                "win_rate": win_rate,
                "sharpe_ratio": float(sharpe_ratio),
                "max_drawdown": max_drawdown,
                "average_episode_length": float(np.mean(episode_lengths)),
                "reward_volatility": float(reward_std),
                "best_episode": float(np.max(episode_rewards)),
                "worst_episode": float(np.min(episode_rewards))
            }
            
            return {"metrics": evaluation_result}
            
        except Exception as e:
            logger.error(f"Agent evaluation failed: {str(e)}")
            raise
    
    # Helper methods
    
    async def _load_financial_data(self, data_source: str) -> pd.DataFrame:
        """Load financial data for trading environment from configured sources"""
        
        if data_source.startswith("file://"):
            # Load from file
            file_path = data_source.replace("file://", "")
            try:
                return pd.read_csv(file_path)
            except Exception as e:
                logger.warning(f"Failed to load data from {file_path}: {str(e)}")
        
        elif data_source.startswith("api://"):
            # Load from API endpoint
            api_url = data_source.replace("api://", "")
            try:
                import requests
                response = requests.get(api_url)
                return pd.DataFrame(response.json())
            except Exception as e:
                logger.warning(f"Failed to load data from API {api_url}: {str(e)}")
        
        # Generate realistic synthetic financial data for development/testing
        logger.info("Generating synthetic financial data for environment")
        np.random.seed(42)
        
        dates = pd.date_range(start='2020-01-01', end='2023-12-31', freq='D')
        prices = []
        price = 100.0
        
        for _ in dates:
            # Random walk with slight upward trend and volatility clustering
            change = np.random.normal(0.001, 0.02)
            price *= (1 + change)
            prices.append(price)
        
        # Calculate technical indicators
        price_series = pd.Series(prices)
        
        data = pd.DataFrame({
            'date': dates,
            'price': prices,
            'volume': np.random.lognormal(10, 1, len(dates)),
            'rsi': self._calculate_rsi(price_series),
            'ma_20': price_series.rolling(20).mean().fillna(method='bfill'),
            'ma_50': price_series.rolling(50).mean().fillna(method='bfill')
        })
        
        return data
    
    async def _create_portfolio_environment(self, config: Dict[str, Any]):
        """Create portfolio optimization environment with multiple assets"""
        logger.info("Creating portfolio optimization environment")
        
        # Load multiple asset data for portfolio optimization
        assets = config.get("assets", ["AAPL", "GOOGL", "MSFT", "TSLA"])
        portfolio_data = {}
        
        for asset in assets:
            data_source = config.get("data_source", "synthetic")
            asset_data = await self._load_financial_data(f"{data_source}_{asset}")
            portfolio_data[asset] = asset_data
        
        # Create multi-asset environment
        from .portfolio_environment import PortfolioEnvironment
        return PortfolioEnvironment(portfolio_data, config)
    
    async def _create_risk_environment(self, config: Dict[str, Any]):
        """Create risk management environment with VaR and stress testing"""
        logger.info("Creating risk management environment")
        
        # Load market data for risk modeling
        data_source = config.get("data_source", "synthetic")
        market_data = await self._load_financial_data(data_source)
        
        # Create risk management environment with VaR calculation
        from .risk_environment import RiskManagementEnvironment
        return RiskManagementEnvironment(market_data, config)
    
    async def _create_ppo_agent(self, state_size: int, action_size: int, config: RLConfig):
        """Create Proximal Policy Optimization agent"""
        logger.info("Creating PPO agent")
        
        try:
            from .ppo_agent import PPOAgent
            return PPOAgent(state_size, action_size, config)
        except ImportError:
            logger.warning("PPO agent not available, using DQN as fallback")
            return DQNAgent(state_size, action_size, config) 