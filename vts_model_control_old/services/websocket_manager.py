from fastapi import WebSocket
from typing import List, Dict
import json
import asyncio


class ConnectionManager:
    def __init__(self):
        # 按路径分组的连接字典
        self.connections_by_path: Dict[str, List[WebSocket]] = {}
        # 为了向后兼容，保留原有的全局连接列表
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, path: str = "default"):
        """连接WebSocket并可选择指定路径分组"""
        await websocket.accept()
        self.active_connections.append(websocket)

        # 按路径分组
        if path not in self.connections_by_path:
            self.connections_by_path[path] = []
        self.connections_by_path[path].append(websocket)

    def disconnect(self, websocket: WebSocket):
        """断开连接并从所有组中移除"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # 从所有路径组中移除
        for path, connections in self.connections_by_path.items():
            if websocket in connections:
                connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"Error sending personal message: {e}")  # Or use logger
            # Consider removing connection if send fails repeatedly

    async def broadcast(self, message: str):
        """向所有连接广播消息（向后兼容）"""
        await self._broadcast_to_connections(self.active_connections, message)

    async def broadcast_to_path(self, path: str, message: str):
        """向指定路径的连接广播消息"""
        if path in self.connections_by_path:
            await self._broadcast_to_connections(
                self.connections_by_path[path], message
            )

    async def _broadcast_to_connections(
        self, connections: List[WebSocket], message: str
    ):
        """内部方法：向指定连接列表广播消息"""
        if not connections:
            return

        # Create a list of tasks for sending messages
        tasks = []
        disconnected_sockets = []
        for connection in connections:
            # Create a task for each send operation
            tasks.append(connection.send_text(message))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Log the error and mark the connection for removal if send failed
                print(
                    f"Error broadcasting message to a websocket: {result}"
                )  # Or use logger
                disconnected_sockets.append(connections[i])

        # Remove connections that failed to send
        for ws in disconnected_sockets:
            self.disconnect(ws)

    async def broadcast_json(self, data: Dict):
        """向所有连接广播JSON消息（向后兼容）"""
        await self.broadcast(json.dumps(data))

    async def broadcast_json_to_path(self, path: str, data: Dict):
        """向指定路径的连接广播JSON消息"""
        await self.broadcast_to_path(path, json.dumps(data))


manager = ConnectionManager()
