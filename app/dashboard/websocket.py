"""WebSocket Server streaming real-time ticks, footprint frames, and decision triggers."""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect


class DashboardWebSocketManager:
    """Manages connected frontend WebSocket clients, broadcasting telemetry frames."""

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)

    async def broadcast_json(self, message: Dict) -> None:
        """Broadcast real-time state dictionary to all connected dashboard clients."""
        disconnected_clients = set()
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                disconnected_clients.add(connection)

        for stale_conn in disconnected_clients:
            self.disconnect(stale_conn)

    async def handle_client(self, websocket: WebSocket) -> None:
        """Client connection lifecycle handling heartbeats and telemetry streams."""
        await self.connect(websocket)
        try:
            # Send initial greeting/handshake frame
            await websocket.send_json({
                "type": "HANDSHAKE",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "CONNECTED",
                "system": "FO-X 5M Dashboard Stream"
            })

            while True:
                # Keep connection alive & handle incoming pings
                data = await websocket.receive_text()
                try:
                    payload = json.loads(data)
                    if payload.get("type") == "PING":
                        await websocket.send_json({"type": "PONG", "timestamp": datetime.now(timezone.utc).isoformat()})
                except Exception:
                    pass
        except WebSocketDisconnect:
            self.disconnect(websocket)
        except Exception:
            self.disconnect(websocket)


ws_manager = DashboardWebSocketManager()
