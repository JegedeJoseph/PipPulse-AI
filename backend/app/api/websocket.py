"""
WebSocket API
Real-time signal and news updates via WebSocket
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any, Optional
import json
import asyncio
from datetime import datetime
import logging
import time

from app.schemas import WebSocketMessage

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 1.0
HEARTBEAT_INTERVAL = 30
MESSAGE_TIMEOUT = 5.0


class ConnectionMetrics:
    """Track metrics for a WebSocket connection"""

    def __init__(self):
        self.connected_at = datetime.utcnow()
        self.last_message_at = datetime.utcnow()
        self.messages_sent = 0
        self.messages_received = 0
        self.total_latency = 0.0
        self.message_latencies = []

    def record_message_sent(self):
        self.messages_sent += 1
        self.last_message_at = datetime.utcnow()

    def record_message_received(self):
        self.messages_received += 1
        self.last_message_at = datetime.utcnow()

    def record_latency(self, latency_ms: float):
        self.message_latencies.append(latency_ms)
        self.total_latency += latency_ms
        # Keep last 100 latencies for memory efficiency
        if len(self.message_latencies) > 100:
            self.total_latency -= self.message_latencies.pop(0)

    def get_average_latency(self) -> float:
        if not self.message_latencies:
            return 0.0
        return self.total_latency / len(self.message_latencies)

    def get_connection_duration(self) -> float:
        """Get connection duration in seconds"""
        return (datetime.utcnow() - self.connected_at).total_seconds()


class ConnectionManager:
    """Manage WebSocket connections"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[WebSocket, Dict[str, Any]] = {}
        self.metrics: Dict[WebSocket, ConnectionMetrics] = {}
        self.connection_lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, subscriptions: Dict[str, Any] = None):
        """Accept a new WebSocket connection"""
        try:
            await websocket.accept()
            async with self.connection_lock:
                self.active_connections.append(websocket)
                self.subscriptions[websocket] = subscriptions or {}
                self.metrics[websocket] = ConnectionMetrics()

            logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

            # Send welcome message
            await self.send_personal_message(
                websocket,
                {
                    "type": "connected",
                    "data": {
                        "message": "Connected to PipPulse AI WebSocket",
                        "timestamp": datetime.utcnow().isoformat(),
                        "connection_id": id(websocket)
                    }
                }
            )
        except Exception as e:
            logger.error(f"Error accepting connection: {e}")
            raise

    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket"""
        async def _cleanup():
            async with self.connection_lock:
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)
                    logger.info(f"Client disconnected. Remaining connections: {len(self.active_connections)}")
                if websocket in self.subscriptions:
                    del self.subscriptions[websocket]
                if websocket in self.metrics:
                    metrics = self.metrics[websocket]
                    logger.info(
                        f"Connection stats - Duration: {metrics.get_connection_duration():.2f}s, "
                        f"Sent: {metrics.messages_sent}, Received: {metrics.messages_received}, "
                        f"Avg Latency: {metrics.get_average_latency():.2f}ms"
                    )
                    del self.metrics[websocket]

        try:
            asyncio.create_task(_cleanup())
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    async def send_personal_message(self, websocket: WebSocket, message: Dict[str, Any], retries: int = 0):
        """Send a message to a specific client with retry logic"""
        start_time = time.time()

        try:
            await asyncio.wait_for(websocket.send_json(message), timeout=MESSAGE_TIMEOUT)

            # Record successful send
            if websocket in self.metrics:
                self.metrics[websocket].record_message_sent()
                latency_ms = (time.time() - start_time) * 1000
                self.metrics[websocket].record_latency(latency_ms)

        except asyncio.TimeoutError:
            logger.warning(f"Message send timeout after {MESSAGE_TIMEOUT}s")
            if retries < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)
                await self.send_personal_message(websocket, message, retries + 1)
            else:
                logger.error(f"Message send failed after {MAX_RETRIES} retries")
                self.disconnect(websocket)

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients"""
        if not self.active_connections:
            logger.debug("No active connections to broadcast to")
            return

        disconnected = []
        async with self.connection_lock:
            connections_copy = self.active_connections.copy()

        for connection in connections_copy:
            try:
                await self.send_personal_message(connection, message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_to_subscribers(self, message_type: str, message: Dict[str, Any]):
        """Broadcast to clients subscribed to a specific message type"""
        disconnected = []
        async with self.connection_lock:
            connections_copy = self.active_connections.copy()

        for connection in connections_copy:
            try:
                subscriptions = self.subscriptions.get(connection, {})

                # Check if client is subscribed to this message type
                if subscriptions.get(message_type, True):
                    await self.send_personal_message(connection, message)

            except Exception as e:
                logger.error(f"Error broadcasting to subscriber: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)

    def get_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics for all connections"""
        if not self.metrics:
            return {
                "total_connections": 0,
                "avg_latency_ms": 0.0,
                "total_messages_sent": 0,
                "total_messages_received": 0
            }

        total_latency = sum(m.get_average_latency() for m in self.metrics.values())
        total_messages_sent = sum(m.messages_sent for m in self.metrics.values())
        total_messages_received = sum(m.messages_received for m in self.metrics.values())

        return {
            "total_connections": len(self.metrics),
            "avg_latency_ms": total_latency / len(self.metrics) if self.metrics else 0.0,
            "total_messages_sent": total_messages_sent,
            "total_messages_received": total_messages_received
        }


# Global connection manager
manager = ConnectionManager()


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket, client_id: str = None):
    """Main WebSocket endpoint"""
    try:
        await manager.connect(websocket)
    except Exception as e:
        logger.error(f"Failed to establish connection: {e}")
        return

    try:
        while True:
            # Receive message from client with timeout
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=MESSAGE_TIMEOUT * 2)
            except asyncio.TimeoutError:
                logger.warning("Client message receive timeout")
                break

            # Track received message
            if websocket in manager.metrics:
                manager.metrics[websocket].record_message_received()

            # Handle different message types
            message_type = data.get("type", "unknown")

            if message_type == "subscribe":
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
                await manager.send_personal_message(websocket, {
                    "type": "pong",
                    "data": {
                        "timestamp": datetime.utcnow().isoformat()
                    }
                })

            elif message_type == "get_status":
                metrics = manager.metrics.get(websocket, ConnectionMetrics())
                await manager.send_personal_message(websocket, {
                    "type": "status",
                    "data": {
                        "connected": True,
                        "subscriptions": manager.subscriptions.get(websocket, {}),
                        "connection_count": manager.get_connection_count(),
                        "avg_latency_ms": metrics.get_average_latency(),
                        "messages_sent": metrics.messages_sent,
                        "messages_received": metrics.messages_received,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                })

            else:
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
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)



@router.websocket("/signals")
async def signals_websocket(websocket: WebSocket):
    """WebSocket endpoint for signal updates only"""
    try:
        await manager.connect(websocket, {"signals": True})
    except Exception as e:
        logger.error(f"Failed to establish signals connection: {e}")
        return

    try:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)

            if websocket in manager.active_connections:
                await manager.send_personal_message(websocket, {
                    "type": "heartbeat",
                    "data": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "connection_id": id(websocket)
                    }
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Signals WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/news")
async def news_websocket(websocket: WebSocket):
    """WebSocket endpoint for news updates only"""
    try:
        await manager.connect(websocket, {"news": True})
    except Exception as e:
        logger.error(f"Failed to establish news connection: {e}")
        return

    try:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)

            if websocket in manager.active_connections:
                await manager.send_personal_message(websocket, {
                    "type": "heartbeat",
                    "data": {
                        "timestamp": datetime.utcnow().isoformat(),
                        "connection_id": id(websocket)
                    }
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"News WebSocket error: {e}")
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
    logger.info(f"Signal broadcasted to {manager.get_connection_count()} connections")


async def broadcast_news(news_item: Dict[str, Any]):
    """Broadcast a new news item to all subscribers"""
    message = {
        "type": "news",
        "data": news_item,
        "timestamp": datetime.utcnow().isoformat()
    }

    await manager.broadcast_to_subscribers("news", message)
    logger.info(f"News broadcasted to {manager.get_connection_count()} connections")


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
    logger.error(f"Error broadcasted to {manager.get_connection_count()} connections: {error}")


# Export manager for use in other modules
__all__ = ["manager", "broadcast_signal", "broadcast_news", "broadcast_error"]

