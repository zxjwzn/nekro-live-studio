import asyncio
from abc import ABC, abstractmethod

class BaseAnimation(ABC):
    """所有动画的基类，提供启动和停止逻辑"""
    def __init__(self, plugin, config, logger):
        self.plugin = plugin
        self.config = config
        self.logger = logger
        self._task = None

    @abstractmethod
    async def run(self, shutdown_event: asyncio.Event):
        """执行动画主循环，子类实现
        
        Args:
            shutdown_event: 全局关闭事件，设置时应当优雅退出
        """
        pass

    def start(self, shutdown_event: asyncio.Event):
        """启动动画任务"""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run(shutdown_event))

    async def stop(self):
        """停止动画任务"""
        if self._task and not self._task.done():
            cancel_timeout = 0.5  # 允许取消操作最多等待0.5秒
            
            # 取消任务
            self._task.cancel()
            
            # 添加超时机制确保任务能被取消
            cancel_deadline = asyncio.get_event_loop().time() + cancel_timeout
            
            while not self._task.done() and asyncio.get_event_loop().time() < cancel_deadline:
                try:
                    # 使用短超时等待任务结束
                    await asyncio.wait_for(asyncio.shield(self._task), timeout=0.1)
                    break  # 任务完成，退出循环
                except asyncio.TimeoutError:
                    # 超时但任务仍在运行，继续等待直到达到最大超时
                    pass
                except asyncio.CancelledError:
                    # 任务已取消
                    break
                except Exception as e:
                    self.logger.error(f"停止动画时出错: {e}")
                    break
            
            # 确保我们不会继续等待已取消的任务
            if not self._task.done():
                self.logger.warning("停止动画任务超时，继续执行关闭流程")
