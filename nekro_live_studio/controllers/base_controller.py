import asyncio
import contextlib
from abc import ABC, abstractmethod
from enum import Enum
from typing import Generic, Optional, TypeVar

from ..clients.vtube_studio.exceptions import (
    VTSConnectionError,
)
from ..clients.vtube_studio.plugin import plugin
from ..utils.logger import logger
from .base_config import ControllerConfig
from .config_manager import config_manager

TConfig = TypeVar("TConfig", bound=ControllerConfig)


class AnimationType(Enum):
    """动画类型枚举"""
    IDLE = "idle"  # 空闲循环动画
    ONESHOT = "oneshot"  # 一次性动画


class BaseController(Generic[TConfig], ABC):
    """动画控制器基类，负责生命周期管理和通用功能"""

    def __init__(self):
        self.plugin = plugin
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None

    @property
    @abstractmethod
    def config(self) -> TConfig:
        """获取此控制器的配置部分"""
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def get_animation_type(cls) -> AnimationType:
        """获取动画类型"""

    def save_config(self) -> None:
        """保存配置"""
        config_manager.dump_config()

    @property
    def is_running(self) -> bool:
        """检查动画是否正在运行"""
        return self._task is not None and not self._task.done()

    @property
    def is_idle_animation(self) -> bool:
        """检查是否为空闲动画"""
        return self.get_animation_type() == AnimationType.IDLE

    async def start(self,*args, **kwargs):
        """启动动画"""
        if self.is_running:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(*args, **kwargs))

    async def stop(self):
        """停止动画"""
        if not self.is_running:
            return
        self._stop_event.set()
        if self._task:
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def stop_without_wait(self):
        """停止动画，不等待"""
        if not self.is_running:
            return
        self._stop_event.set()
        if self._task:
            self._task.cancel()

    async def _run(self,*args, **kwargs):
        """主运行逻辑，根据动画类型选择执行方式"""
        try:
            if not self.config.ENABLED:
                return

            if self.get_animation_type() == AnimationType.IDLE:
                await self._run_loop()
            else:
                await self.execute(*args, **kwargs)
        except asyncio.CancelledError:
            pass
        except VTSConnectionError:
            # 插件已断开，退出
            pass
        except Exception as e:
            if not self._stop_event.is_set():
                logger.error(f"{self.__class__.__name__} 执行出错: {e}", exc_info=True)

    async def _run_loop(self):
        """循环执行逻辑（仅用于空闲动画）"""
        while not self._stop_event.is_set():
            try:
                await self.run_cycle()
            except asyncio.CancelledError:
                break
            except VTSConnectionError:
                break
            except Exception as e:
                if not self._stop_event.is_set():
                    logger.error(f"{self.__class__.__name__} 执行周期出错: {e}", exc_info=True)

    async def run_cycle(self):
        """子类实现一次动画循环逻辑（仅用于空闲动画）"""
        raise NotImplementedError("空闲动画必须实现 run_cycle 方法")

    async def execute(self,*args, **kwargs):
        """子类实现一次性动画执行逻辑（用于非循环动画）"""
        raise NotImplementedError("非循环动画必须实现 execute 方法")


class IdleController(BaseController[TConfig], ABC):
    """空闲动画控制器基类"""

    @classmethod
    def get_animation_type(cls) -> AnimationType:
        return AnimationType.IDLE

    @abstractmethod
    async def run_cycle(self):
        """子类实现一次动画循环逻辑"""

    async def execute(self,*args, **kwargs):
        """空闲动画不需要实现此方法"""


class OneShotController(BaseController[TConfig], ABC):
    """一次性动画控制器基类"""

    @classmethod
    def get_animation_type(cls) -> AnimationType:
        return AnimationType.ONESHOT

    async def run_cycle(self):
        """一次性动画不需要实现此方法"""

    @abstractmethod
    async def execute(self,*args, **kwargs):
        """子类实现一次性动画执行逻辑"""
