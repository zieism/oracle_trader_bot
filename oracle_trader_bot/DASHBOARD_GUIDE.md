# Real-Time Dashboard Testing Guide

## Overview
The Oracle Trader Bot now includes a comprehensive real-time dashboard with WebSocket integration.

## Accessing the Dashboard
- **Main Dashboard**: http://localhost:8000/dashboard/
- **API Documentation**: http://localhost:8000/docs
- **Settings Interface**: http://localhost:8000/api/ui

## Dashboard Features

### 1. Real-Time WebSocket Connection
- Auto-connects on page load
- Shows connection status in navbar
- Automatic reconnection with exponential backoff
- Heartbeat system for connection health

### 2. Trading Controls
- **Start Bot**: Initiates the trading bot
- **Stop Bot**: Stops the trading bot
- **Restart Bot**: Restarts the trading bot
- **Test WebSocket**: Emits a test event
- **Refresh Data**: Manually refreshes dashboard data
- **Pause Updates**: Pauses chart updates

### 3. Live Metrics
- **Bot Status**: Current bot state (running/stopped)
- **Daily P&L**: Today's profit/loss
- **Active Positions**: Number of open positions
- **Total Trades**: Total executed trades

### 4. System Health Monitoring
- **CPU Usage**: Real-time CPU utilization
- **Memory Usage**: Real-time memory utilization
- **WebSocket Connections**: Active connection count

### 5. Market Data
- Live price updates
- 24-hour change percentages
- Trading pair status

### 6. Recent Trades
- Last 10 executed trades
- Trade details (symbol, side, quantity, price, P&L)
- Real-time updates

### 7. Live Events Feed
- Real-time system events
- Trading notifications
- Error alerts
- WebSocket messages

## API Endpoints

### Dashboard API
- `GET /dashboard/` - Main dashboard page
- `GET /dashboard/api/dashboard-data` - Dashboard data
- `GET /dashboard/api/trading-metrics` - Trading metrics
- `GET /dashboard/api/system-status` - System status
- `POST /dashboard/api/bot-control/{action}` - Bot control
- `POST /dashboard/api/emit-test-event` - Test event emission

### WebSocket Endpoints
- `WS /dashboard/ws/dashboard` - Main dashboard WebSocket
- `WS /dashboard/ws/trading` - Trading-specific WebSocket
- `WS /dashboard/ws/monitor` - System monitoring WebSocket

## WebSocket Message Types

### Client to Server
```json
{
    "type": "subscribe",
    "topic": "trading"
}
```

### Server to Client
```json
{
    "type": "trade_executed",
    "data": {
        "symbol": "BTC/USDT",
        "side": "buy",
        "quantity": 0.001,
        "price": 45000
    },
    "timestamp": 1641024000
}
```

## Event Types
- **Trading**: trade_executed, order_placed, position_opened
- **Market Data**: price_update, ticker_update
- **Bot Status**: bot_started, bot_stopped, bot_error
- **System**: system_alert, health_update
- **Portfolio**: portfolio_update, balance_update

## Testing Steps

1. **Start the Application**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Open Dashboard**
   - Navigate to http://localhost:8000/dashboard/
   - Verify WebSocket connection shows "Connected"

3. **Test Trading Controls**
   - Click "Test WebSocket" button
   - Verify event appears in Live Events feed
   - Try Start/Stop Bot controls

4. **Monitor Real-Time Updates**
   - Watch Live Events for new messages
   - Monitor connection count updates
   - Verify system metrics updates

## Browser Compatibility
- Chrome/Chromium (recommended)
- Firefox
- Safari
- Edge

## Mobile Responsive
The dashboard is fully responsive and works on:
- Desktop (1200px+)
- Tablet (768px - 1199px)
- Mobile (320px - 767px)

## Troubleshooting

### WebSocket Connection Issues
- Check server logs for connection errors
- Verify firewall/proxy settings
- Confirm WebSocket support in browser

### Performance Issues
- Use "Pause Updates" to reduce CPU usage
- Clear event log periodically
- Check browser console for errors

### Missing Data
- Click "Refresh Data" button
- Check database connection
- Verify API endpoints are responding

## Production Deployment Notes
- Enable HTTPS for WebSocket security
- Configure proper CORS origins
- Set up SSL termination
- Monitor WebSocket connection limits
- Implement rate limiting
- Add authentication/authorization