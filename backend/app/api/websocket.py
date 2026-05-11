"""
WebSocket API
Real-time signal and news updates via WebSocket
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import asyncio
from datetime import datetime

from app.schemas import WebSocketMessage

router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, subscriptions: Dict[str, Any] = None):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = subscriptions or {}

        # Send welcome message
        await self.send_personal_message(
            websocket,
            {
                "type": "connected",
                "data": {
                    "message": "Connected to PipPulse AI WebSocket",
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )

    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]

    async def send_personal_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send a message to a specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"Error sending message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients"""
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_to_subscribers(self, message_type: str, message: Dict[str, Any]):
        """Broadcast to clients subscribed to a specific message type"""
        disconnected = []

        for connection in self.active_connections:
            try:
                subscriptions = self.subscriptions.get(connection, {})

                # Check if client is subscribed to this message type
                if subscriptions.get(message_type, True):
                    await connection.send_json(message)

            except Exception as e:
                print(f"Error broadcasting to subscriber: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint"""
    await manager.connect(websocket)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            # Handle different message types
            message_type = data.get("type", "unknown")

            if message_type == "subscribe":
                # Handle subscription
                subscriptions = data.get("subscriptions", {})
                manager.subscriptions[websocket] = subscriptions

                await manager.send_personal_message(websocket, {
                    "type": "subscribed",
                    "data": {
                        "subscriptions": subscriptions,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                })

            elif message_type == "unsubscribe":
                # Handle unsubscription
                message_type_to_unsub = data.get("message_type")
                if message_type_to_unsub and websocket in manager.subscriptions:
                    manager.subscriptions[websocket][message_type_to_unsub] = False

                await manager.send_personal_message(websocket, {
                    "type": "unsubscribed",
                    "data": {
                        "message_type": message_type_to_unsub,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                })

            elif message_type == "ping":
                # Respond to ping
                await manager.send_personal_message(websocket, {
                    "type": "pong",
                    "data": {
                        "timestamp": datetime.utcnow().isoformat()
                    }
                })

            elif message_type == "get_status":
                # Send connection status
                await manager.send_personal_message(websocket, {
                    "type": "status",
                    "data": {
                        "connected": True,
                        "subscriptions": manager.subscriptions.get(websocket, {}),
                        "connection_count": manager.get_connection_count(),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                })

            else:
                # Unknown message type
                await manager.send_personal_message(websocket, {
                    "type": "error",
                    "data": {
                        "message": f"Unknown message type: {message_type}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/signals")
async def signals_websocket(websocket: WebSocket):
    """WebSocket endpoint for signal updates only"""
    await manager.connect(websocket, {"signals": True})

    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(30)

            # Send heartbeat
            await manager.send_personal_message(websocket, {
                "type": "heartbeat",
                "data": {
                    "timestamp": datetime.utcnow().isoformat()
                }
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"Signals WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/news")
async def news_websocket(websocket: WebSocket):
    """WebSocket endpoint for news updates only"""
    await manager.connect(websocket, {"news": True})

    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(30)

            # Send heartbeat
            await manager.send_personal_message(websocket, {
                "type": "heartbeat",
                "data": {
                    "timestamp": datetime.utcnow().isoformat()
                }
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"News WebSocket error: {e}")
        manager.disconnect(websocket)


# Helper functions for broadcasting
async def broadcast_signal(signal: Dict[str, Any]):
    """Broadcast a new signal to all subscribers"""
    message = {
        "type": "signal",
        "data": signal,
        "timestamp": datetime.utcnow().isoformat()
    }

    await manager.broadcast_to_subscribers("signals", message)


async def broadcast_news(news_item: Dict[str, Any]):
    """Broadcast a new news item to all subscribers"""
    message = {
        "type": "news",
        "data": news_item,
        "timestamp": datetime.utcnow().isoformat()
    }

    await manager.broadcast_to_subscribers("news", message)


async def broadcast_error(error: str):
    """Broadcast an error to all connected clients"""
    message = {
        "type": "error",
        "data": {
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }
    }

    await manager.broadcast(message)


# Export manager for use in other modules
__all__ = ["manager", "broadcast_signal", "broadcast_news", "broadcast_error"]
