import asyncio
from typing import List

from fastapi import WebSocket
from utils.logger import logger


class SubtitleBroadcaster:
    def __init__(self):
        self.connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.connections.append(websocket)
        logger.info(f"字幕客户端已连接: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)
        logger.info(f"字幕客户端已断开: {websocket.client}")

    async def broadcast(self, message: str):
        async with self._lock:
            if not self.connections:
                return

            tasks = [connection.send_text(message) for connection in self.connections]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理发送失败的连接
            for websocket, result in zip(self.connections[:], results):
                if isinstance(result, Exception):
                    logger.warning(f"发送字幕到 {websocket.client} 失败: {result}")
                    self.disconnect(websocket)


# 创建一个全局单例
subtitle_broadcaster = SubtitleBroadcaster() 