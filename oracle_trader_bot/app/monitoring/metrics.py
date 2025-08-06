# app/monitoring/metrics.py
import time
import logging
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from app.core.config import settings


logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Prometheus metrics collector for Oracle Trader Bot.
    
    Tracks key trading and system metrics.
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        
        # Trading metrics
        self.trades_total = Counter(
            'oracle_trader_trades_total',
            'Total number of trades executed',
            ['exchange', 'symbol', 'side', 'status'],
            registry=self.registry
        )
        
        self.trade_duration = Histogram(
            'oracle_trader_trade_duration_seconds',
            'Time taken to execute trades',
            ['exchange', 'symbol'],
            registry=self.registry
        )
        
        self.trade_profit_usd = Histogram(
            'oracle_trader_trade_profit_usd',
            'Profit/loss per trade in USD',
            ['exchange', 'symbol'],
            registry=self.registry
        )
        
        # Portfolio metrics
        self.portfolio_balance = Gauge(
            'oracle_trader_portfolio_balance_usd',
            'Total portfolio balance in USD',
            ['exchange'],
            registry=self.registry
        )
        
        self.portfolio_pnl = Gauge(
            'oracle_trader_portfolio_pnl_usd',
            'Portfolio unrealized PnL in USD',
            ['exchange'],
            registry=self.registry
        )
        
        # Exchange metrics
        self.exchange_requests = Counter(
            'oracle_trader_exchange_requests_total',
            'Total API requests to exchanges',
            ['exchange', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.exchange_latency = Histogram(
            'oracle_trader_exchange_latency_seconds',
            'Exchange API response latency',
            ['exchange', 'endpoint'],
            registry=self.registry
        )
        
        self.exchange_errors = Counter(
            'oracle_trader_exchange_errors_total',
            'Exchange API errors',
            ['exchange', 'error_type'],
            registry=self.registry
        )
        
        # Arbitrage metrics
        self.arbitrage_opportunities = Counter(
            'oracle_trader_arbitrage_opportunities_total',
            'Arbitrage opportunities detected',
            ['symbol', 'buy_exchange', 'sell_exchange'],
            registry=self.registry
        )
        
        self.arbitrage_executed = Counter(
            'oracle_trader_arbitrage_executed_total',
            'Arbitrage trades executed',
            ['symbol', 'buy_exchange', 'sell_exchange', 'status'],
            registry=self.registry
        )
        
        self.arbitrage_profit = Histogram(
            'oracle_trader_arbitrage_profit_usd',
            'Arbitrage profit per execution',
            ['symbol', 'buy_exchange', 'sell_exchange'],
            registry=self.registry
        )
        
        # System metrics
        self.system_health = Gauge(
            'oracle_trader_system_health',
            'System health status (1=healthy, 0=unhealthy)',
            ['service'],
            registry=self.registry
        )
        
        self.active_connections = Gauge(
            'oracle_trader_active_connections',
            'Number of active connections',
            ['type'],
            registry=self.registry
        )
        
        # Risk metrics
        self.risk_score = Gauge(
            'oracle_trader_risk_score',
            'Current risk score (0-100)',
            registry=self.registry
        )
        
        self.daily_loss = Gauge(
            'oracle_trader_daily_loss_usd',
            'Daily realized loss in USD',
            registry=self.registry
        )
        
        self.position_size = Gauge(
            'oracle_trader_position_size_usd',
            'Position size in USD',
            ['exchange', 'symbol', 'side'],
            registry=self.registry
        )
    
    def record_trade(self, exchange: str, symbol: str, side: str, status: str, 
                    duration_seconds: float, profit_usd: float = 0):
        """Record a trade execution."""
        self.trades_total.labels(
            exchange=exchange,
            symbol=symbol,
            side=side,
            status=status
        ).inc()
        
        self.trade_duration.labels(
            exchange=exchange,
            symbol=symbol
        ).observe(duration_seconds)
        
        if profit_usd != 0:
            self.trade_profit_usd.labels(
                exchange=exchange,
                symbol=symbol
            ).observe(profit_usd)
    
    def update_portfolio_balance(self, exchange: str, balance_usd: float):
        """Update portfolio balance."""
        self.portfolio_balance.labels(exchange=exchange).set(balance_usd)
    
    def update_portfolio_pnl(self, exchange: str, pnl_usd: float):
        """Update portfolio PnL."""
        self.portfolio_pnl.labels(exchange=exchange).set(pnl_usd)
    
    def record_exchange_request(self, exchange: str, endpoint: str, status: str, 
                               latency_seconds: float):
        """Record an exchange API request."""
        self.exchange_requests.labels(
            exchange=exchange,
            endpoint=endpoint,
            status=status
        ).inc()
        
        self.exchange_latency.labels(
            exchange=exchange,
            endpoint=endpoint
        ).observe(latency_seconds)
    
    def record_exchange_error(self, exchange: str, error_type: str):
        """Record an exchange error."""
        self.exchange_errors.labels(
            exchange=exchange,
            error_type=error_type
        ).inc()
    
    def record_arbitrage_opportunity(self, symbol: str, buy_exchange: str, sell_exchange: str):
        """Record an arbitrage opportunity."""
        self.arbitrage_opportunities.labels(
            symbol=symbol,
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange
        ).inc()
    
    def record_arbitrage_execution(self, symbol: str, buy_exchange: str, sell_exchange: str,
                                  status: str, profit_usd: float):
        """Record arbitrage execution."""
        self.arbitrage_executed.labels(
            symbol=symbol,
            buy_exchange=buy_exchange,
            sell_exchange=sell_exchange,
            status=status
        ).inc()
        
        if profit_usd > 0:
            self.arbitrage_profit.labels(
                symbol=symbol,
                buy_exchange=buy_exchange,
                sell_exchange=sell_exchange
            ).observe(profit_usd)
    
    def update_system_health(self, service: str, is_healthy: bool):
        """Update system health status."""
        self.system_health.labels(service=service).set(1 if is_healthy else 0)
    
    def update_active_connections(self, connection_type: str, count: int):
        """Update active connection count."""
        self.active_connections.labels(type=connection_type).set(count)
    
    def update_risk_score(self, score: float):
        """Update risk score."""
        self.risk_score.set(score)
    
    def update_daily_loss(self, loss_usd: float):
        """Update daily loss."""
        self.daily_loss.set(loss_usd)
    
    def update_position_size(self, exchange: str, symbol: str, side: str, size_usd: float):
        """Update position size."""
        self.position_size.labels(
            exchange=exchange,
            symbol=symbol,
            side=side
        ).set(size_usd)
    
    def get_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry).decode('utf-8')
    
    def get_metrics_dict(self) -> Dict[str, Any]:
        """Get metrics as dictionary for JSON API."""
        # This is a simplified version - in practice you'd parse the metrics
        return {
            "timestamp": int(time.time()),
            "trades_total": self.trades_total._value.sum(),
            "arbitrage_opportunities": self.arbitrage_opportunities._value.sum(),
            "arbitrage_executed": self.arbitrage_executed._value.sum(),
            "system_health": {
                family.name: {
                    str(sample.labels): sample.value 
                    for sample in family.samples
                }
                for family in self.registry.collect()
                if family.name == 'oracle_trader_system_health'
            }
        }


# Global metrics collector instance
metrics_collector = MetricsCollector()