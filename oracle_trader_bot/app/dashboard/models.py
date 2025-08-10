# app/dashboard/models.py
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from datetime import datetime


class DashboardData(BaseModel):
    """Data model for dashboard information."""
    timestamp: float
    bot_status: str
    active_positions: int
    total_trades: int
    daily_pnl: float
    total_balance: float
    market_data: Dict[str, Any]
    recent_trades: List[Dict[str, Any]]
    system_health: Dict[str, Any]
    account_overview: Optional[List[Dict[str, Any]]] = []


class ChartData(BaseModel):
    """Data model for chart information."""
    labels: List[str]
    datasets: List[Dict[str, Any]]
    

class MarketTicker(BaseModel):
    """Market ticker data model."""
    symbol: str
    price: float
    change_24h: float
    volume: float
    timestamp: datetime


class TradingMetrics(BaseModel):
    """Trading performance metrics."""
    total_trades: int
    profitable_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    average_pnl_per_trade: float
    max_profit: float
    max_loss: float
    max_drawdown: float


class SystemStatus(BaseModel):
    """System status information."""
    bot_running: bool
    uptime: float
    cpu_usage: float
    memory_usage: float
    websocket_connections: int
    last_update: float