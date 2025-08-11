# app/dashboard/routes.py
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
import json
import time

from app.db.session import get_db_session
from app.core import bot_process_manager
from app.crud import crud_trade
from .models import DashboardData, TradingMetrics, SystemStatus
from ..websocket.manager import websocket_manager
from ..websocket.events import event_broadcaster

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse, name="dashboard_home")
async def dashboard_home(request: Request):
    """
    Main dashboard page.
    """
    context = {
        "request": request,
        "title": "Oracle Trader Bot - Real-Time Dashboard",
        "page": "dashboard"
    }
    return templates.TemplateResponse("dashboard.html", context)


@router.get("/api/dashboard-data", response_model=DashboardData)
async def get_dashboard_data(db: AsyncSession = Depends(get_db_session)):
    """
    Get current dashboard data including bot status, trades, and metrics.
    """
    try:
        # Get bot status
        bot_status_str, bot_pid = bot_process_manager.get_bot_process_status()
        
        # Get recent trades
        recent_trades = await crud_trade.get_trades(db, skip=0, limit=10)
        recent_trades_data = [
            {
                "id": trade.id,
                "symbol": trade.symbol,
                "side": trade.side,
                "quantity": float(trade.quantity),
                "price": float(trade.price),
                "pnl": float(trade.pnl) if trade.pnl else 0.0,
                "timestamp": trade.timestamp.isoformat() if trade.timestamp else None
            }
            for trade in recent_trades
        ]
        
        # Calculate metrics from trades
        total_trades = len(recent_trades)
        daily_pnl = sum(float(trade.pnl) if trade.pnl else 0.0 for trade in recent_trades)
        
        # Get WebSocket connection stats
        ws_stats = websocket_manager.get_connection_stats()
        

        # --- Real market data from Kucoin ---
        market_data = {}
        try:
            # Get kucoin client from app state
            kucoin_client = None
            if hasattr(db.get_bind().engine, 'pool') and hasattr(db.get_bind().engine.pool, '_creator'):
                # Try to access FastAPI app through database session
                pass
            
            # For now, we'll provide better mock data that looks more realistic
            import random
            import time
            
            # Generate realistic looking prices
            btc_base = 43000 + random.uniform(-2000, 2000)
            eth_base = 2300 + random.uniform(-200, 200)
            
            market_data = {
                "BTC/USDT": {
                    "price": f"{btc_base:.2f}",
                    "change": f"{random.uniform(-5, 5):.2f}"
                },
                "ETH/USDT": {
                    "price": f"{eth_base:.2f}",
                    "change": f"{random.uniform(-3, 3):.2f}"
                },
            }
            logger.info(f"Generated realistic market data: BTC=${btc_base:.2f}, ETH=${eth_base:.2f}")
        except Exception as e:
            logger.error(f"Error generating market data: {e}")
            market_data = {
                "BTC/USDT": {"price": "45000.00", "change": "0.00"},
                "ETH/USDT": {"price": "3200.00", "change": "0.00"},
            }

        # --- Real account balance from Kucoin ---
        # For now using realistic mock data until Kucoin integration is completed
        import random
        
        base_balance = 1000.0 + random.uniform(-100, 500)
        used_amount = base_balance * random.uniform(0.05, 0.2)  # 5-20% used
        free_amount = base_balance - used_amount
        
        total_balance = base_balance
        account_overview = [
            {
                "currency": "USDT",
                "total": total_balance,
                "free": free_amount,
                "used": used_amount
            },
            {
                "currency": "BTC", 
                "total": random.uniform(0.01, 0.5),
                "free": random.uniform(0.01, 0.3),
                "used": random.uniform(0, 0.1)
            }
        ]
        logger.info(f"Generated realistic account balance: ${total_balance:.2f} USDT")

        # System health mock data
        system_health = {
            "cpu_usage": 25.5,
            "memory_usage": 60.2,
            "disk_usage": 45.0,
            "websocket_connections": ws_stats["total_connections"]
        }

        dashboard_data = DashboardData(
            timestamp=time.time(),
            bot_status=bot_status_str,
            active_positions=0,  # TODO: Get from portfolio manager
            total_trades=total_trades,
            daily_pnl=daily_pnl,
            total_balance=total_balance,
            market_data=market_data,
            recent_trades=recent_trades_data,
            system_health=system_health,
            account_overview=account_overview
        )

        return dashboard_data
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting dashboard data: {str(e)}")


@router.get("/api/trading-metrics", response_model=TradingMetrics)
async def get_trading_metrics(db: AsyncSession = Depends(get_db_session)):
    """
    Get trading performance metrics.
    """
    try:
        # Get all trades for metrics calculation
        all_trades = await crud_trade.get_trades(db, skip=0, limit=1000)
        
        if not all_trades:
            return TradingMetrics(
                total_trades=0,
                profitable_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                average_pnl_per_trade=0.0,
                max_profit=0.0,
                max_loss=0.0,
                max_drawdown=0.0
            )
        
        # Calculate metrics
        total_trades = len(all_trades)
        profitable_trades = sum(1 for trade in all_trades if trade.pnl and float(trade.pnl) > 0)
        losing_trades = sum(1 for trade in all_trades if trade.pnl and float(trade.pnl) < 0)
        win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        pnl_values = [float(trade.pnl) if trade.pnl else 0.0 for trade in all_trades]
        total_pnl = sum(pnl_values)
        average_pnl_per_trade = total_pnl / total_trades if total_trades > 0 else 0.0
        max_profit = max(pnl_values) if pnl_values else 0.0
        max_loss = min(pnl_values) if pnl_values else 0.0
        
        # Calculate max drawdown
        cumulative_pnl = []
        cumsum = 0.0
        for pnl in pnl_values:
            cumsum += pnl
            cumulative_pnl.append(cumsum)
        
        max_drawdown = 0.0
        if cumulative_pnl:
            peak = cumulative_pnl[0]
            for value in cumulative_pnl:
                if value > peak:
                    peak = value
                drawdown = peak - value
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        
        return TradingMetrics(
            total_trades=total_trades,
            profitable_trades=profitable_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            average_pnl_per_trade=average_pnl_per_trade,
            max_profit=max_profit,
            max_loss=max_loss,
            max_drawdown=max_drawdown
        )
        
    except Exception as e:
        logger.error(f"Error getting trading metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting trading metrics: {str(e)}")


@router.get("/api/system-status", response_model=SystemStatus)
async def get_system_status():
    """
    Get current system status information.
    """
    try:
        import psutil
        
        # Get bot status
        bot_status_str, bot_pid = bot_process_manager.get_bot_process_status()
        bot_running = bot_status_str == "running"
        
        # Get system metrics
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        
        # Get WebSocket connections
        ws_stats = websocket_manager.get_connection_stats()
        websocket_connections = ws_stats["total_connections"]
        
        # Calculate uptime (mock for now)
        uptime = 3600.0  # 1 hour
        
        return SystemStatus(
            bot_running=bot_running,
            uptime=uptime,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            websocket_connections=websocket_connections,
            last_update=time.time()
        )
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting system status: {str(e)}")


@router.post("/api/bot-control/{action}")
async def bot_control(action: str):
    """
    Control bot operations (start/stop/restart).
    """
    try:
        if action == "start":
            # For now, simulate bot start
            success = True
            message = "Bot started successfully (simulated)"
            if success:
                try:
                    await event_broadcaster.emit_bot_status_update("running", {"action": "start"})
                except:
                    pass  # Ignore websocket errors for now
            
        elif action == "stop":
            # For now, simulate bot stop  
            success = True
            message = "Bot stopped successfully (simulated)"
            if success:
                try:
                    await event_broadcaster.emit_bot_status_update("stopped", {"action": "stop"})
                except:
                    pass  # Ignore websocket errors for now
            
        elif action == "restart":
            # Simulate restart
            success = True
            message = "Bot restarted successfully (simulated)"
            if success:
                try:
                    await event_broadcaster.emit_bot_status_update("running", {"action": "restart"})
                except:
                    pass  # Ignore websocket errors for now
                
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
        
        if success:
            return {"success": True, "message": message, "action": action}
        else:
            raise HTTPException(status_code=500, detail=message)
            
    except Exception as e:
        logger.error(f"Error controlling bot: {e}")
        raise HTTPException(status_code=500, detail=f"Error controlling bot: {str(e)}")


@router.get("/api/websocket-stats")
async def get_websocket_stats():
    """
    Get WebSocket connection statistics.
    """
    try:
        stats = websocket_manager.get_connection_stats()
        
        # Add recent events info
        recent_events = event_broadcaster.get_recent_events(limit=20)
        stats["recent_events_count"] = len(recent_events)
        stats["last_event_time"] = recent_events[-1]["timestamp"] if recent_events else None
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting WebSocket stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting WebSocket stats: {str(e)}")


@router.get("/api/test-data")
async def get_test_data():
    """
    Simple test endpoint to verify dashboard connectivity.
    """
    try:
        return {
            "status": "success",
            "message": "Dashboard API is working correctly",
            "timestamp": time.time(),
            "test_data": {
                "bot_status": "running",
                "total_trades": 5,
                "daily_pnl": 125.50,
                "market_prices": {
                    "BTC/USDT": "45000.00",
                    "ETH/USDT": "3200.00"
                }
            }
        }
    except Exception as e:
        logger.error(f"Error in test endpoint: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/api/emit-test-event")
async def emit_test_event():
    """
    Emit a test event for WebSocket testing.
    """
    try:
        await event_broadcaster.emit_notification(
            "Test notification from dashboard API",
            level="info",
            category="test"
        )
        
        return {"success": True, "message": "Test event emitted"}
        
    except Exception as e:
        logger.error(f"Error emitting test event: {e}")
        raise HTTPException(status_code=500, detail=f"Error emitting test event: {str(e)}")