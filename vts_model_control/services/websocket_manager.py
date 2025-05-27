from fastapi import WebSocket
from typing import List, Dict
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"Error sending personal message: {e}") # Or use logger
            # Consider removing connection if send fails repeatedly

    async def broadcast(self, message: str):
        # Create a list of tasks for sending messages
        tasks = []
        disconnected_sockets = []
        for connection in self.active_connections:
            # Create a task for each send operation
            tasks.append(connection.send_text(message))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Log the error and mark the connection for removal if send failed
                print(f"Error broadcasting message to a websocket: {result}") # Or use logger
                disconnected_sockets.append(self.active_connections[i])
        
        # Remove connections that failed to send
        for ws in disconnected_sockets:
            self.disconnect(ws)


    async def broadcast_json(self, data: Dict):
        await self.broadcast(json.dumps(data))

manager = ConnectionManager() 