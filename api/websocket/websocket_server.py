"""
WebSocket Server - Real-time bidirectional communication
Manages WebSocket connections and real-time data push
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Set, Any
import uuid

from utils.trace_logger import trace, trace_async_calls
from models.schemas import WebSocketMessage


class WebSocketConnection:
    """Represents a WebSocket connection"""

    def __init__(self, connection_id: str, user_id: str, websocket):
        self.connection_id = connection_id
        self.user_id = user_id
        self.websocket = websocket
        self.connected_at = datetime.now()
        self.last_message_at = datetime.now()
        self.messages_sent = 0
        self.messages_received = 0


class WebSocketServer:
    """
    WebSocket server for real-time bidirectional communication
    All WebSocket activity is traced to files for debugging
    """

    def __init__(self, event_dispatcher):
        self.event_dispatcher = event_dispatcher
        self.connections: Dict[str, WebSocketConnection] = {}
        self.user_connections: Dict[str, Set[str]] = {}  # user_id -> connection_ids
        self.is_running = False

        trace.info("WebSocketServer initialized", module=__name__, function="__init__")

    @trace_async_calls
    async def start(self):
        """Start WebSocket server"""
        self.is_running = True

        # Subscribe to relevant events for broadcasting
        await self.event_dispatcher.subscribe("data.processed", self._on_data_processed)
        await self.event_dispatcher.subscribe("alert.raised", self._on_alert_raised)
        await self.event_dispatcher.subscribe("state.change", self._on_state_change)

        trace.info("WebSocketServer started", module=__name__, function="start")

    @trace_async_calls
    async def stop(self):
        """Stop WebSocket server"""
        self.is_running = False

        # Close all connections
        for conn_id in list(self.connections.keys()):
            await self.disconnect(conn_id)

        trace.info(
            "WebSocketServer stopped",
            context={"connections_closed": len(self.connections)},
            module=__name__,
            function="stop"
        )

    @trace_async_calls
    async def connect(self, user_id: str, websocket) -> str:
        """Handle new WebSocket connection"""

        connection_id = str(uuid.uuid4())

        connection = WebSocketConnection(connection_id, user_id, websocket)
        self.connections[connection_id] = connection

        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)

        trace.info(
            f"WebSocket connection established: {connection_id}",
            context={
                "connection_id": connection_id,
                "user_id": user_id,
                "total_connections": len(self.connections)
            },
            module=__name__,
            function="connect"
        )

        # Send welcome message
        await self.send_to_connection(
            connection_id,
            WebSocketMessage(
                type="connection.established",
                payload={
                    "connection_id": connection_id,
                    "user_id": user_id,
                    "server_time": datetime.now().isoformat()
                }
            )
        )

        return connection_id

    @trace_async_calls
    async def disconnect(self, connection_id: str):
        """Handle WebSocket disconnection"""

        connection = self.connections.get(connection_id)
        if not connection:
            return

        user_id = connection.user_id

        # Remove from tracking
        del self.connections[connection_id]
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        trace.info(
            f"WebSocket connection closed: {connection_id}",
            context={
                "connection_id": connection_id,
                "user_id": user_id,
                "duration_seconds": (datetime.now() - connection.connected_at).total_seconds(),
                "messages_sent": connection.messages_sent,
                "messages_received": connection.messages_received
            },
            module=__name__,
            function="disconnect"
        )

    @trace_async_calls
    async def send_to_connection(self, connection_id: str, message: WebSocketMessage):
        """Send message to a specific connection"""

        connection = self.connections.get(connection_id)
        if not connection:
            trace.warning(
                f"Cannot send to non-existent connection: {connection_id}",
                module=__name__,
                function="send_to_connection"
            )
            return

        try:
            message_data = {
                "type": message.type,
                "payload": message.payload,
                "timestamp": message.timestamp.isoformat()
            }

            await connection.websocket.send_text(json.dumps(message_data))
            connection.messages_sent += 1
            connection.last_message_at = datetime.now()

            trace.debug(
                f"Message sent to connection {connection_id}",
                context={
                    "connection_id": connection_id,
                    "message_type": message.type,
                    "user_id": connection.user_id
                },
                module=__name__,
                function="send_to_connection"
            )

        except Exception as e:
            trace.error(
                f"Error sending message to connection {connection_id}",
                context={
                    "connection_id": connection_id,
                    "message_type": message.type
                },
                module=__name__,
                function="send_to_connection",
                exception=e
            )

            # Disconnect on error
            await self.disconnect(connection_id)

    @trace_async_calls
    async def send_to_user(self, user_id: str, message: WebSocketMessage):
        """Send message to all connections of a user"""

        connection_ids = self.user_connections.get(user_id, set())

        if not connection_ids:
            trace.debug(
                f"No active connections for user {user_id}",
                module=__name__,
                function="send_to_user"
            )
            return

        trace.debug(
            f"Broadcasting to user {user_id}",
            context={
                "user_id": user_id,
                "connections": len(connection_ids),
                "message_type": message.type
            },
            module=__name__,
            function="send_to_user"
        )

        # Send to all user connections
        tasks = [
            self.send_to_connection(conn_id, message)
            for conn_id in connection_ids
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    @trace_async_calls
    async def broadcast(self, message: WebSocketMessage, exclude_connection: str = None):
        """Broadcast message to all connections"""

        connection_ids = [
            conn_id for conn_id in self.connections.keys()
            if conn_id != exclude_connection
        ]

        trace.debug(
            "Broadcasting to all connections",
            context={
                "recipients": len(connection_ids),
                "message_type": message.type
            },
            module=__name__,
            function="broadcast"
        )

        tasks = [
            self.send_to_connection(conn_id, message)
            for conn_id in connection_ids
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _on_data_processed(self, event):
        """Handle data.processed event - push updates to user"""
        user_id = event.payload.get("user_id")
        if not user_id:
            return

        message = WebSocketMessage(
            type="vitality_update",
            payload={
                "workflow_id": event.payload.get("workflow_id"),
                "status": "processed",
                "timestamp": datetime.now().isoformat()
            }
        )

        await self.send_to_user(user_id, message)

    async def _on_alert_raised(self, event):
        """Handle alert.raised event - push alerts"""
        user_id = event.payload.get("user_id")
        if user_id:
            message = WebSocketMessage(
                type="alert",
                payload=event.payload
            )
            await self.send_to_user(user_id, message)
        else:
            # System-wide alert
            await self.broadcast(WebSocketMessage(type="alert", payload=event.payload))

    async def _on_state_change(self, event):
        """Handle state.change event - push state updates"""
        user_id = event.payload.get("user_id")
        if user_id:
            message = WebSocketMessage(
                type="state_update",
                payload=event.payload
            )
            await self.send_to_user(user_id, message)

    @trace_async_calls
    async def handle_client_message(self, connection_id: str, message_data: str):
        """Handle message received from client"""

        connection = self.connections.get(connection_id)
        if not connection:
            return

        try:
            data = json.loads(message_data)
            connection.messages_received += 1
            connection.last_message_at = datetime.now()

            trace.debug(
                f"Message received from connection {connection_id}",
                context={
                    "connection_id": connection_id,
                    "user_id": connection.user_id,
                    "message_type": data.get("type")
                },
                module=__name__,
                function="handle_client_message"
            )

            # Handle different message types
            message_type = data.get("type")

            if message_type == "ping":
                # Respond to ping
                await self.send_to_connection(
                    connection_id,
                    WebSocketMessage(type="pong", payload={"server_time": datetime.now().isoformat()})
                )

            elif message_type == "subscribe":
                # Handle subscription request
                trace.info(
                    f"Subscription request from {connection_id}",
                    context={"topics": data.get("topics", [])},
                    module=__name__,
                    function="handle_client_message"
                )

            # Add more message type handlers as needed

        except json.JSONDecodeError as e:
            trace.error(
                f"Invalid JSON from connection {connection_id}",
                context={"connection_id": connection_id},
                module=__name__,
                function="handle_client_message",
                exception=e
            )

        except Exception as e:
            trace.error(
                f"Error handling client message from {connection_id}",
                context={"connection_id": connection_id},
                module=__name__,
                function="handle_client_message",
                exception=e
            )

    def get_websocket_metrics(self) -> Dict[str, Any]:
        """Get WebSocket server metrics"""
        return {
            "total_connections": len(self.connections),
            "total_users": len(self.user_connections),
            "is_running": self.is_running,
            "total_messages_sent": sum(c.messages_sent for c in self.connections.values()),
            "total_messages_received": sum(c.messages_received for c in self.connections.values())
        }
