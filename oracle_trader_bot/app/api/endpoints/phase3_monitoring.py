# app/api/endpoints/phase3_monitoring.py
import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime, timedelta

from app.monitoring.dashboard import performance_dashboard
from app.monitoring.alerting import alerting_manager, AlertSeverity, AlertChannel
from app.portfolio.portfolio_manager import portfolio_manager
from app.portfolio.risk_manager import risk_manager
from app.portfolio.performance_tracker import performance_tracker
from app.config.config_manager import config_manager
from app.security.encryption import encryption_manager


logger = logging.getLogger(__name__)

router = APIRouter()


# Dashboard and Monitoring Endpoints
@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_data():
    """Get real-time dashboard data with system and trading metrics."""
    try:
        # Update dashboard with latest data
        await performance_dashboard.update_dashboard_data()
        
        dashboard_data = performance_dashboard.get_dashboard_data()
        return {
            "success": True,
            "data": dashboard_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=Dict[str, Any])
async def get_health_status():
    """Get overall system health status."""
    try:
        health_status = performance_dashboard.get_health_status()
        portfolio_summary = portfolio_manager.get_portfolio_summary()
        risk_summary = risk_manager.get_risk_summary()
        
        return {
            "success": True,
            "health": health_status,
            "portfolio": portfolio_summary,
            "risk": risk_summary,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Portfolio Management Endpoints
@router.get("/portfolio/summary", response_model=Dict[str, Any])
async def get_portfolio_summary():
    """Get portfolio management summary."""
    try:
        summary = portfolio_manager.get_portfolio_summary()
        return {
            "success": True,
            "portfolio": summary,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting portfolio summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portfolio/calculate-position-size", response_model=Dict[str, Any])
async def calculate_position_size(
    symbol: str,
    entry_price: float,
    market_volatility: float,
    strategy_signal_strength: float,
    account_balance: float,
    current_positions: int,
    max_positions: int,
    risk_tolerance: float = 0.02
):
    """Calculate optimal position size for a trade."""
    try:
        result = await portfolio_manager.calculate_position_size(
            symbol=symbol,
            entry_price=entry_price,
            market_volatility=market_volatility,
            strategy_signal_strength=strategy_signal_strength,
            account_balance=account_balance,
            current_positions=current_positions,
            max_positions=max_positions,
            risk_tolerance=risk_tolerance
        )
        
        return {
            "success": True,
            "position_size": {
                "size_usd": result.size_usd,
                "size_base": result.size_base,
                "leverage": result.leverage,
                "margin_required": result.margin_required,
                "risk_percentage": result.risk_percentage,
                "reason": result.reason
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error calculating position size: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Risk Management Endpoints
@router.get("/risk/summary", response_model=Dict[str, Any])
async def get_risk_summary():
    """Get comprehensive risk management summary."""
    try:
        summary = risk_manager.get_risk_summary()
        return {
            "success": True,
            "risk": summary,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting risk summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk/initialize-daily-tracking", response_model=Dict[str, Any])
async def initialize_daily_tracking(account_balance: float):
    """Initialize daily risk tracking with starting balance."""
    try:
        await risk_manager.initialize_daily_tracking(account_balance)
        return {
            "success": True,
            "message": f"Daily tracking initialized with balance: ${account_balance:.2f}",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error initializing daily tracking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk/emergency-stop", response_model=Dict[str, Any])
async def activate_emergency_stop(reason: str):
    """Activate emergency stop for all trading activities."""
    try:
        await risk_manager.activate_emergency_stop(reason)
        return {
            "success": True,
            "message": f"Emergency stop activated: {reason}",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error activating emergency stop: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk/deactivate-emergency-stop", response_model=Dict[str, Any])
async def deactivate_emergency_stop():
    """Deactivate emergency stop (resume trading)."""
    try:
        risk_manager.deactivate_emergency_stop()
        return {
            "success": True,
            "message": "Emergency stop deactivated - trading resumed",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error deactivating emergency stop: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Performance Tracking Endpoints
@router.get("/performance/summary", response_model=Dict[str, Any])
async def get_performance_summary():
    """Get performance tracking summary."""
    try:
        summary = performance_tracker.get_performance_summary()
        return {
            "success": True,
            "performance": summary,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/metrics", response_model=Dict[str, Any])
async def get_performance_metrics(
    days: int = Query(30, description="Number of days for performance calculation")
):
    """Get detailed performance metrics for specified period."""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        metrics = await performance_tracker.calculate_performance_metrics(start_date=start_date)
        
        return {
            "success": True,
            "metrics": {
                "period_start": metrics.period_start.isoformat(),
                "period_end": metrics.period_end.isoformat(),
                "total_trades": metrics.total_trades,
                "winning_trades": metrics.winning_trades,
                "losing_trades": metrics.losing_trades,
                "win_rate": metrics.win_rate,
                "total_pnl": metrics.total_pnl,
                "gross_profit": metrics.gross_profit,
                "gross_loss": metrics.gross_loss,
                "profit_factor": metrics.profit_factor,
                "avg_win": metrics.avg_win,
                "avg_loss": metrics.avg_loss,
                "largest_win": metrics.largest_win,
                "largest_loss": metrics.largest_loss,
                "max_drawdown": metrics.max_drawdown,
                "max_runup": metrics.max_runup,
                "sharpe_ratio": metrics.sharpe_ratio,
                "sortino_ratio": metrics.sortino_ratio,
                "calmar_ratio": metrics.calmar_ratio,
                "total_fees": metrics.total_fees,
                "return_on_investment": metrics.return_on_investment
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/daily", response_model=Dict[str, Any])
async def get_daily_performance(
    days: int = Query(30, description="Number of days to retrieve")
):
    """Get daily performance data."""
    try:
        daily_data = performance_tracker.get_daily_performance(days)
        return {
            "success": True,
            "daily_performance": daily_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting daily performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Alerting Endpoints
@router.get("/alerts/recent", response_model=Dict[str, Any])
async def get_recent_alerts(
    hours: int = Query(24, description="Number of hours to look back")
):
    """Get recent alerts."""
    try:
        alerts = alerting_manager.get_recent_alerts(hours)
        summary = alerting_manager.get_alert_summary()
        
        return {
            "success": True,
            "alerts": alerts,
            "summary": summary,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting recent alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/send", response_model=Dict[str, Any])
async def send_alert(
    title: str,
    message: str,
    severity: str,
    source: str = "api"
):
    """Send a custom alert."""
    try:
        severity_enum = AlertSeverity(severity.upper())
        
        await alerting_manager.send_alert(
            title=title,
            message=message,
            severity=severity_enum,
            source=source
        )
        
        return {
            "success": True,
            "message": f"Alert sent: {title}",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Configuration Management Endpoints
@router.get("/config/summary", response_model=Dict[str, Any])
async def get_config_summary():
    """Get configuration management summary."""
    try:
        # Initialize config manager if needed
        if not config_manager._initialized:
            await config_manager.initialize()
        
        summary = config_manager.get_config_summary()
        return {
            "success": True,
            "config": summary,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting config summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/get", response_model=Dict[str, Any])
async def get_config_value(key: str):
    """Get configuration value by key."""
    try:
        if not config_manager._initialized:
            await config_manager.initialize()
        
        value = await config_manager.get_config(key)
        return {
            "success": True,
            "key": key,
            "value": value,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting config value: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/set", response_model=Dict[str, Any])
async def set_config_value(key: str, value: Any, user: str = "api"):
    """Set configuration value."""
    try:
        if not config_manager._initialized:
            await config_manager.initialize()
        
        success = await config_manager.set_config(key, value, user=user)
        
        return {
            "success": success,
            "message": f"Configuration {'updated' if success else 'update failed'}: {key}",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error setting config value: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/history", response_model=Dict[str, Any])
async def get_config_history(limit: int = Query(50, description="Number of recent changes")):
    """Get configuration change history."""
    try:
        history = config_manager.get_config_history(limit)
        return {
            "success": True,
            "history": history,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting config history: {e}")
        raise HTTPException(status_code=500, detail=str(e))