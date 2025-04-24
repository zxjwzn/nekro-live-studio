import asyncio
from abc import ABC, abstractmethod
from services.plugin import plugin
from utils.logger import logger
from vts_client.exceptions import ConnectionError as VTSConnectionError

class BaseController(ABC):
    """动画控制器基类，负责生命周期管理（start/stop）"""
    def __init__(self):
        self.plugin = plugin
        self._stop_event = asyncio.Event()
        self._task = None

    async def start(self):
        """启动动画循环"""
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self):
        """停止动画循环"""
        self._stop_event.set()
        if self._task:
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    async def stop_without_wait(self):
        """停止动画循环，不等待"""
        self._stop_event.set()
        if self._task:
            self._task.cancel()

    async def _run(self):
        """主循环，调用 run_cycle 并处理异常"""
        while not self._stop_event.is_set():
            try:
                await self.run_cycle()
            except asyncio.CancelledError:
                break
            except VTSConnectionError:
                # 插件已断开，退出循环
                break
            except Exception as e:
                # 仅在非关闭阶段记录其他异常
                if not self._stop_event.is_set():
                    logger.error(f"{self.__class__.__name__} 执行周期出错: {e}", exc_info=True)

    @abstractmethod
    async def run_cycle(self):
        """子类实现一次动画循环逻辑"""
        pass 