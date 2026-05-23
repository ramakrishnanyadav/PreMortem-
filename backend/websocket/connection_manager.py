"""
connection_manager.py
---------------------
Manages WebSocket connections and broadcasts events.
"""
import structlog
from fastapi import WebSocket
from typing import List, Any

logger = structlog.get_logger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("websocket_connected", num_connections=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("websocket_disconnected", num_connections=len(self.active_connections))

    async def broadcast(self, message: Any):
        """
        Broadcasts a message to all active connections.
        Wraps sends in try/except and cleans up dead connections.
        """
        dead_connections = []
        for connection in self.active_connections:
            try:
                if isinstance(message, dict) or isinstance(message, list):
                    await connection.send_json(message)
                else:
                    await connection.send_text(str(message))
            except Exception as e:
                logger.warning("websocket_send_failed", error=str(e))
                dead_connections.append(connection)
                
        for connection in dead_connections:
            self.disconnect(connection)
