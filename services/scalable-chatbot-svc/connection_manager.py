"""Connection manager for scalable chatbot service."""

from datetime import datetime
from typing import Any, Dict, Set

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections for scalable chat sessions."""

    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_connections: Dict[str, Set[str]] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, session_id: str, client_id: str) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket

        if session_id not in self.session_connections:
            self.session_connections[session_id] = set()
        self.session_connections[session_id].add(client_id)

        self.connection_metadata[client_id] = {
            "session_id": session_id,
            "connected_at": datetime.now(),
            "last_activity": datetime.now(),
        }

    def disconnect(self, client_id: str) -> None:
        """Remove a WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        for session_id, connections in list(self.session_connections.items()):
            connections.discard(client_id)
            if not connections:
                del self.session_connections[session_id]

        if client_id in self.connection_metadata:
            del self.connection_metadata[client_id]

    async def send_personal_message(self, message: str, client_id: str) -> None:
        """Send message to specific client."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(message)
            except Exception:
                self.disconnect(client_id)

    async def send_to_session(self, message: str, session_id: str) -> None:
        """Send message to all clients in a session."""
        if session_id in self.session_connections:
            for client_id in list(self.session_connections[session_id]):
                await self.send_personal_message(message, client_id)

    async def broadcast(self, message: str) -> None:
        """Broadcast message to all active connections."""
        for client_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, client_id)

    async def cleanup_stale_connections(self, timeout_minutes: int = 10) -> None:
        """Clean up connections that have been inactive longer than timeout."""
        current_time = datetime.now()
        stale_connections = []

        for client_id, metadata in self.connection_metadata.items():
            last_activity = metadata.get("last_activity")
            if last_activity and (current_time - last_activity).total_seconds() > timeout_minutes * 60:
                stale_connections.append(client_id)

        for client_id in stale_connections:
            print(f"Cleaning up stale connection: {client_id}")
            self.disconnect(client_id)
