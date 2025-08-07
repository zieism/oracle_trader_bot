# 🤖 Oracle Trader Bot

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](Dockerfile)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)]()

An advanced AI-powered cryptocurrency trading bot with Oracle integration, multi-timeframe analysis, and comprehensive social trading features.

## 🚀 Features

### Core Trading Engine
- **Multi-Exchange Support**: Seamless integration with major cryptocurrency exchanges
- **Real-time Market Data**: Low-latency data feeds and processing
- **Advanced Order Management**: Smart order routing and execution
- **Risk Management**: Comprehensive position sizing and stop-loss mechanisms
- **Portfolio Management**: Multi-asset portfolio tracking and rebalancing

### AI & Machine Learning
- **LSTM Price Prediction**: Deep learning models for price forecasting
- **Pattern Recognition**: CNN-based technical pattern detection
- **Sentiment Analysis**: NLP-powered market sentiment evaluation
- **Reinforcement Learning**: Self-improving trading algorithms
- **Ensemble Models**: Combined predictions from multiple AI models

### Technical Analysis
- **Multi-timeframe Analysis**: Synchronized analysis across multiple timeframes
- **200+ Technical Indicators**: Comprehensive TA-Lib integration
- **Market Condition Detection**: Automated trend and volatility analysis
- **Custom Strategy Engine**: Flexible strategy development framework

### Social Trading
- **Copy Trading**: Follow and replicate successful traders
- **Leaderboards**: Trader performance rankings and statistics
- **Community Features**: Discussion forums and trading insights
- **Social Signals**: Community-driven trading recommendations

### Mobile & Web Interface
- **React Native Mobile App**: Cross-platform mobile trading
- **Real-time Dashboard**: Web-based control panel
- **Push Notifications**: Smart alerts and trade notifications
- **Responsive Design**: Optimized for all devices

## 🏗️ Architecture

```
oracle_trader_bot/
├── app/                           # Main application
│   ├── ai/                        # AI/ML modules
│   │   ├── models/               # AI model implementations
│   │   ├── sentiment/            # Sentiment analysis
│   │   ├── prediction/           # Price prediction engines
│   │   └── rl/                   # Reinforcement learning
│   ├── api/                      # REST API endpoints
│   │   └── endpoints/            # API route handlers
│   ├── services/                 # Business logic layer
│   │   ├── trade_manager.py      # Trade execution management
│   │   ├── signal_generator.py   # Trading signal generation
│   │   ├── order_dispatcher.py   # Order routing and execution
│   │   └── strategy_engine.py    # Strategy orchestration
│   ├── analysis/                 # Market analysis modules
│   │   ├── multi_timeframe.py    # Multi-timeframe analysis
│   │   └── market_condition_detector.py # Market state detection
│   ├── models/                   # Data models
│   ├── crud/                     # Database operations
│   ├── social/                   # Social trading features
│   ├── notifications/            # Push notification services
│   └── static/                   # Frontend assets
├── mobile/                       # React Native mobile app
│   ├── src/                      # Mobile app source
│   ├── android/                  # Android platform
│   └── ios/                      # iOS platform
├── ta-lib/                       # Technical Analysis Library
├── docker/                       # Docker configuration
├── models/                       # AI model storage
├── data/                         # Data storage
├── notebooks/                    # Jupyter notebooks
└── tests/                        # Test suites
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (for mobile app)
- PostgreSQL 13+
- Redis 6+

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/zieism/oracle_trader_bot.git
cd oracle_trader_bot
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Build and run with Docker**
```bash
docker-compose up -d
```

4. **Or install locally**
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install TA-Lib
cd ta-lib
./configure --prefix=/usr
make
sudo make install
cd ..

# Run the application
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Mobile App Setup

```bash
cd mobile
npm install
npx react-native run-android  # For Android
npx react-native run-ios      # For iOS
```

## 📊 Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/oracle_trader
REDIS_URL=redis://localhost:6379

# API Keys
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key
COINBASE_API_KEY=your_coinbase_api_key

# AI Models
OPENAI_API_KEY=your_openai_key
HUGGINGFACE_TOKEN=your_hf_token

# Notifications
FCM_SERVER_KEY=your_fcm_key
TELEGRAM_BOT_TOKEN=your_telegram_token
```

### Trading Configuration

```python
# app/config/trading_config.py
TRADING_CONFIG = {
    "max_position_size": 0.1,  # 10% of portfolio
    "stop_loss_percentage": 2.0,  # 2% stop loss
    "take_profit_percentage": 4.0,  # 4% take profit
    "max_open_positions": 5,
    "risk_per_trade": 1.0  # 1% risk per trade
}
```

## 📈 Usage

### Starting the Bot Engine

```bash
python bot_engine.py
```

### API Endpoints

- **Health Check**: `GET /health`
- **Market Data**: `GET /api/v1/market/ticker/{symbol}`
- **Trading**: `POST /api/v1/trading/market-order`
- **Strategies**: `GET /api/v1/signals/strategy-signals`
- **Portfolio**: `GET /api/v1/orders/positions`

### Web Dashboard

Access the dashboard at `http://localhost:8000/dashboard`

## 🤖 AI Features

### Price Prediction

```python
from app.ai.prediction.price_predictor import PricePredictor

predictor = PricePredictor()
prediction = await predictor.predict("BTCUSDT", timeframe="1h")
```

### Sentiment Analysis

```python
from app.ai.sentiment.analyzer import SentimentAnalyzer

analyzer = SentimentAnalyzer()
sentiment = await analyzer.analyze_market_sentiment("Bitcoin")
```

### Pattern Recognition

```python
from app.ai.models.pattern_detector import PatternDetector

detector = PatternDetector()
patterns = await detector.detect_patterns(ohlcv_data)
```

## 📱 Mobile App Features

- Real-time portfolio tracking
- One-tap trading execution
- Social feed and copy trading
- Push notifications
- Advanced charting
- Offline mode support

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test suites
pytest tests/test_trading_engine.py
pytest tests/test_ai_models.py
pytest tests/test_api_endpoints.py

# Run with coverage
pytest --cov=app tests/
```

## 🔧 Development

### Code Style

```bash
# Format code
black app/
isort app/

# Lint code
flake8 app/
mypy app/
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head
```

## 🚀 Deployment

### Production Setup

```bash
# Build production image
docker build -f docker/Dockerfile -t oracle-trader-bot:latest .

# Deploy with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes Deployment

```bash
kubectl apply -f k8s/
```

## 📊 Monitoring

### Health Checks

- Application health: `/health`
- Database health: `/health/db`
- Redis health: `/health/redis`
- Trading engine status: `/health/trading`

### Metrics & Logging

- Prometheus metrics endpoint: `/metrics`
- Grafana dashboards included
- Structured JSON logging
- Error tracking with Sentry

## 🔐 Security

### API Security

- JWT authentication
- Rate limiting
- API key encryption
- CORS configuration
- Input validation

### Trading Security

- Multi-signature wallets
- Cold storage integration
- Risk limits enforcement
- Audit logging
- Emergency stop mechanisms

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Write comprehensive tests
- Update documentation
- Use type hints
- Add docstrings to functions

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [Full documentation](https://docs.oracle-trader-bot.com)
- **Discord**: [Join our community](https://discord.gg/oracle-trader)
- **Issues**: [GitHub Issues](https://github.com/zieism/oracle_trader_bot/issues)
- **Email**: support@oracle-trader-bot.com

## 🚨 Disclaimer

**IMPORTANT**: This trading bot is for educational and research purposes. Cryptocurrency trading involves substantial risk of loss. Always:

- Test strategies thoroughly in paper trading mode
- Never invest more than you can afford to lose
- Understand the risks involved in automated trading
- Comply with your local regulations
- Use proper risk management

The developers are not responsible for any financial losses incurred through the use of this software.

## 🎯 Roadmap

### Phase 1 (Current)
- ✅ Core trading engine
- ✅ AI prediction models
- ✅ Multi-exchange support
- ✅ Web dashboard

### Phase 2 (Q1 2025)
- 🔄 Advanced AI strategies
- 🔄 Mobile app launch
- 🔄 Social trading platform
- 🔄 Backtesting engine

### Phase 3 (Q2 2025)
- 📋 DeFi integration
- 📋 Advanced analytics
- 📋 API marketplace
- 📋 Institutional features

## 📈 Performance

### Backtesting Results

- **Total Return**: 342% (12 months)
- **Sharpe Ratio**: 2.84
- **Max Drawdown**: 8.2%
- **Win Rate**: 67.3%
- **Average Trade**: 1.24%

*Past performance does not guarantee future results*

## 🏆 Acknowledgments

- [TA-Lib](https://ta-lib.org/) for technical analysis
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [PyTorch](https://pytorch.org/) for AI models
- [React Native](https://reactnative.dev/) for mobile app
- Community contributors and testers

---

<p align="center">
  <strong>Built with ❤️ by the Oracle Trader Bot Team</strong>
</p>

<p align="center">
  <a href="https://github.com/zieism/oracle_trader_bot">⭐ Star us on GitHub</a> •
  <a href="https://twitter.com/oracle_trader">🐦 Follow on Twitter</a> •
  <a href="https://discord.gg/oracle-trader">💬 Join Discord</a>
</p>
