"""Dashboard package init."""

from app.dashboard.api.routes import router as dashboard_router
from app.dashboard.websocket import ws_manager

__all__ = ["dashboard_router", "ws_manager"]
