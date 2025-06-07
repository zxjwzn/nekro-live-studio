from collections import defaultdict
from typing import Dict, List

from fastapi import WebSocket


class WebSocketManager:
    """
    管理WebSocket连接的管理器.
    """

    def __init__(self):
        """
        初始化.
        `active_connections` 的结构: `Dict[str, List[WebSocket]]`
        例如: `{"/ws/danmaku": [websocket1, websocket2]}`
        """
        self.active_connections: Dict[str, List[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, path: str):
        """
        处理新的WebSocket连接.
        """
        await websocket.accept()
        self.active_connections[path].append(websocket)

    def disconnect(self, websocket: WebSocket, path: str):
        """
        处理WebSocket断开连接.
        """
        if websocket in self.active_connections[path]:
            self.active_connections[path].remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """
        向单个WebSocket连接发送文本消息.
        """
        await websocket.send_text(message)

    async def send_personal_json(self, data: dict, websocket: WebSocket):
        """
        向单个WebSocket连接发送JSON消息.
        """
        await websocket.send_json(data)

    async def broadcast_to_path(self, path: str, message: str):
        """
        向特定路径下的所有连接广播文本消息.
        """
        for connection in self.active_connections[path]:
            await connection.send_text(message)

    async def broadcast_json_to_path(self, path: str, data: dict):
        """
        向特定路径下的所有连接广播JSON消息.
        """
        for connection in self.active_connections[path]:
            await connection.send_json(data)


# 创建一个全局的管理器实例
manager = WebSocketManager()
