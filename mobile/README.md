# Oracle Trader Mobile App

## 📱 Phase 7: Mobile & Social Trading Platform

A comprehensive React Native mobile application for the Oracle Trader Bot ecosystem, featuring social trading, real-time notifications, and community engagement.

## 🚀 Features

### Mobile App Core
- **React Native with Expo** - Cross-platform mobile development
- **Real-time Dashboard** - Live portfolio and trading data
- **WebSocket Integration** - Real-time market data and notifications
- **Offline Trading** capabilities for basic functionality

### Social Trading
- **Copy Trading Engine** - Automatically replicate successful traders' moves
- **Trader Leaderboard** - Rankings based on performance metrics
- **Follow System** - Follow top traders and get their signals
- **Social Feed** - Share and discover trading insights

### Push Notifications
- **Smart Alerts** - AI-powered personalized notifications
- **Firebase Cloud Messaging** - Android push notifications
- **Apple Push Notifications** - iOS push notifications
- **Real-time Trading Alerts** - Price movements, trade signals, and market updates

### Community Features
- **Trading Discussions** - Community forums for market analysis
- **Social Analytics** - Community sentiment and trending topics
- **Gamification** - Points, achievements, and leaderboards
- **User Profiles** - Trading stats and social metrics

## 📋 Installation

### Prerequisites
- Node.js 18+
- React Native development environment
- Expo CLI
- iOS Simulator / Android Emulator

### Backend Setup
1. Navigate to the backend directory:
```bash
cd oracle_trader_bot
```

2. Install social trading dependencies:
```bash
pip install -r requirements_social.txt
```

3. Set up environment variables:
```bash
cp .env.mobile .env
# Edit .env with your configuration
```

4. Initialize database with new tables:
```bash
python -c "from app.db.session import Base, async_engine; import asyncio; asyncio.run(Base.metadata.create_all(bind=async_engine))"
```

### Mobile App Setup
1. Navigate to the mobile directory:
```bash
cd mobile
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

4. Run on device/simulator:
```bash
# iOS
npm run ios

# Android
npm run android
```

## 🏗️ Architecture

### Backend Components
```
oracle_trader_bot/
├── app/
│   ├── social/           # Social trading models and services
│   │   ├── models.py     # SQLAlchemy models for social features
│   │   ├── copy_trading.py # Copy trading engine
│   │   └── leaderboard.py  # Trader rankings service
│   ├── notifications/    # Push notification services
│   │   └── push_service.py # FCM and APNS integration
│   ├── alerts/          # Smart alert engine
│   │   └── smart_alerts.py # Personalized alerts
│   ├── gamification/    # Points and achievements
│   │   └── rewards.py   # Gamification engine
│   ├── community/       # Discussion forums
│   │   └── discussions.py # Community features
│   └── api/endpoints/
│       └── social_trading.py # API endpoints
```

### Mobile App Structure
```
mobile/
├── src/
│   ├── components/      # Reusable UI components
│   │   ├── TradingChart.tsx
│   │   ├── SocialFeed.tsx
│   │   ├── OrderPanel.tsx
│   │   └── AlertsComponent.tsx
│   ├── screens/         # Main app screens
│   │   ├── Dashboard.tsx
│   │   ├── Trading.tsx
│   │   ├── Social.tsx
│   │   ├── Community.tsx
│   │   └── Profile.tsx
│   ├── services/        # External integrations
│   │   ├── WebSocketService.ts
│   │   ├── APIService.ts
│   │   └── NotificationService.ts
│   ├── hooks/           # Custom React hooks
│   │   ├── useWebSocket.ts
│   │   ├── useSocialData.ts
│   │   └── useNotifications.ts
│   └── utils/           # Helper functions
└── App.tsx              # Main app component
```

## 🔧 Configuration

### Environment Variables

#### Backend (.env.mobile)
```bash
# API Configuration
MOBILE_API_URL=https://api.oracletrader.com
WEBSOCKET_URL=wss://ws.oracletrader.com

# Firebase Push Notifications
FIREBASE_PROJECT_ID=oracle-trader-app
FIREBASE_PRIVATE_KEY=your_private_key
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@oracle-trader-app.iam.gserviceaccount.com

# Apple Push Notifications
APNS_KEY_ID=your_key_id
APNS_TEAM_ID=your_team_id
APNS_BUNDLE_ID=com.oracletrader.mobile

# Social Features
COPY_TRADING_MAX_FOLLOWERS=1000
LEADERBOARD_UPDATE_INTERVAL=3600
GAMIFICATION_ENABLED=true
```

#### Mobile App (app.json)
```json
{
  "expo": {
    "name": "Oracle Trader Mobile",
    "slug": "oracle-trader-mobile",
    "platforms": ["ios", "android"],
    "notification": {
      "icon": "./assets/notification-icon.png",
      "color": "#ffffff"
    }
  }
}
```

## 📱 Key Features

### 1. Real-time Trading Dashboard
- Live portfolio balance and P&L
- Active positions and recent trades
- Real-time price charts with technical indicators
- Quick trading actions

### 2. Social Trading Platform
- **Copy Trading**: Automatically replicate successful traders
- **Leaderboard**: Rankings by ROI, win rate, and consistency
- **Social Feed**: Share trades, analysis, and insights
- **Follow System**: Get notifications from top traders

### 3. Smart Notifications
- **AI-Powered Alerts**: Personalized based on trading behavior
- **Price Alerts**: Custom price thresholds and targets
- **Social Notifications**: Follower updates and trade copies
- **News Sentiment**: Market-moving news and analysis

### 4. Community Engagement
- **Discussion Forums**: Category-based trading discussions
- **Trending Topics**: Popular market themes and hashtags
- **User Profiles**: Trading statistics and achievements
- **Gamification**: Points, levels, and achievement badges

## 🔄 Real-time Features

### WebSocket Integration
```typescript
// Real-time data subscription
const { portfolio, trades, alerts } = useWebSocket();

// Auto-connect and reconnect
useEffect(() => {
  websocket.connect();
  return () => websocket.disconnect();
}, []);
```

### Push Notifications
```typescript
// Register device for notifications
await notificationService.registerDevice(
  userId, 
  deviceToken, 
  platform
);

// Send trading alert
await pushService.sendTradeAlert(userId, {
  symbol: 'BTCUSDT',
  action: 'buy',
  price: 42300
});
```

## 🎯 Success Metrics

- **📱 Mobile App**: Cross-platform deployment (iOS & Android)
- **⚡ Performance**: 60fps on mid-range devices
- **🔔 Notifications**: 99% delivery rate, 90%+ open rate
- **👥 Social**: 10,000+ engaged community members
- **📊 Copy Trading**: 80%+ successful trade replication
- **🏆 Gamification**: Active points and achievement system

## 🚀 Getting Started

1. **Clone the repository**
2. **Set up the backend** with social trading features
3. **Configure push notifications** (Firebase/APNS)
4. **Install mobile dependencies** and run the app
5. **Test real-time features** and social trading

## 📖 API Documentation

The social trading API provides endpoints for:

- `/api/v1/social/leaderboard` - Get trader rankings
- `/api/v1/social/follow/{trader_id}` - Follow/unfollow traders
- `/api/v1/social/discussions` - Community discussions
- `/api/v1/social/gamification/stats/{user_id}` - User achievements
- `/api/v1/social/notifications/register-device` - Push notification setup

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement mobile features with proper testing
4. Submit a pull request with detailed description

## 📄 License

This project is part of the Oracle Trader Bot ecosystem. See the main repository for license information.