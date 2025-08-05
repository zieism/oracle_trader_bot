# app/dashboard/__init__.py
"""
Dashboard module for real-time trading dashboard interface.
"""

from .routes import router as dashboard_router
from .websocket import dashboard_websocket_router
from .models import DashboardData

__all__ = ["dashboard_router", "dashboard_websocket_router", "DashboardData"]