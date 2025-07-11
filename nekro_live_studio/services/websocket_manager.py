import asyncio
from collections import defaultdict
from typing import Dict, List

from fastapi import WebSocket

from ..utils.logger import logger


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
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, path: str):
        """
        处理新的WebSocket连接.
        """
        await websocket.accept()
        async with self._lock:
            self.active_connections[path].append(websocket)
        logger.info(f"客户端 {websocket.client} 已连接到 {path}")

    async def disconnect(self, websocket: WebSocket, path: str):
        """
        处理WebSocket断开连接.
        """
        async with self._lock:
            if websocket in self.active_connections[path]:
                self.active_connections[path].remove(websocket)
        logger.info(f"客户端 {websocket.client} 已从 {path} 断开")

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
        async with self._lock:
            if not self.active_connections.get(path):
                return

            tasks = [connection.send_text(message) for connection in self.active_connections[path]]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理发送失败的连接
            for websocket, result in zip(self.active_connections[path][:], results):
                if isinstance(result, Exception):
                    logger.warning(f"发送消息到 {websocket.client} 失败: {result}, 将其从 {path} 中移除")
                    self.active_connections[path].remove(websocket)

    async def broadcast_json_to_path(self, path: str, data: dict):
        """
        向特定路径下的所有连接广播JSON消息.
        """
        async with self._lock:
            if not self.active_connections.get(path):
                return

            tasks = [connection.send_json(data) for connection in self.active_connections[path]]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理发送失败的连接
            for websocket, result in zip(self.active_connections[path][:], results):
                if isinstance(result, Exception):
                    logger.warning(f"发送JSON到 {websocket.client} 失败: {result}, 将其从 {path} 中移除")
                    self.active_connections[path].remove(websocket)


# 创建一个全局的管理器实例
manager = WebSocketManager()
