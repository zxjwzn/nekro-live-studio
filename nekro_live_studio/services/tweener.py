import asyncio
import contextlib
import random
from typing import Dict, Optional, Tuple

from ..clients.vtube_studio.plugin import VTSPlugin, plugin
from ..utils.easing import Easing
from ..utils.logger import logger


class Tweener:
    """
    通用的缓动工具类，并内置参数保活功能，以维持对VTS参数的控制。
    """

    def __init__(self, keep_alive_interval: float = 0.8):
        self._plugin = plugin
        self.controlled_params: Dict[str, float] = {}
        self._active_tweens: Dict[str, Tuple[asyncio.Task, int]] = {}
        self._lock = asyncio.Lock()
        self._keep_alive_task: Optional[asyncio.Task] = None
        self._keep_alive_interval = keep_alive_interval

    def start(self, plugin: Optional[VTSPlugin] = None):
        """启动参数保活循环。"""
        if self._keep_alive_task and not self._keep_alive_task.done():
            logger.warning("Tweener 保活任务已在运行中.")
            return
        if plugin:
            self._plugin = plugin
        self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())
        logger.info("Tweener 参数保活任务已启动.")

    async def stop(self):
        """停止参数保活循环。"""
        if self._keep_alive_task:
            self._keep_alive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._keep_alive_task
        logger.info("Tweener 参数保活任务已停止.")

    async def _keep_alive_loop(self):
        """定期发送参数值以保持控制权。"""
        while True:
            try:
                await asyncio.sleep(self._keep_alive_interval)
                async with self._lock:
                    if not self.controlled_params:
                        continue

                    tasks = []
                    for param, value in self.controlled_params.items():
                        if param not in self._active_tweens:
                            tasks.append(self._plugin.set_parameter_value(param, value, mode="set"))
                    if tasks:
                        await asyncio.gather(*tasks)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Tweener 保活循环出错: {e}", exc_info=True)

    async def tween(
        self,
        param: str,
        end: float,
        duration: float,
        easing_func,
        start: Optional[float] = None,
        mode: str = "set",
        fps: int = 60,
        priority: int = 0,
    ):
        """
        优化后的缓动函数：保证在 duration 时间内完成，并由保活机制接管。

        Args:
            param: 参数名称
            end: 目标值
            duration: 缓动持续时间
            easing_func: 缓动函数
            start: 起始值，如果为None则使用当前控制的参数值，如果没有当前值则默认为0
            mode: 设置模式
            fps: 帧率
            priority: 缓动优先级，默认为0。高优先级会中断正在进行的低优先级缓动。
        """
        if not self._plugin:
            logger.error("Tweener 未启动，请先调用 start() 方法.")
            return

        # 确定起始值
        if start is None:
            async with self._lock:
                start = self.controlled_params.get(param, 0.0)

        current_task = asyncio.current_task()
        if not current_task:
            logger.error("无法在 tween 中获取当前任务.")
            return

        # 如果 duration 小于等于 0 或 start 等于 end，则直接设置参数值并返回
        if duration <= 0 or start == end:
            async with self._lock:
                if param in self._active_tweens:
                    _existing_task, existing_priority = self._active_tweens[param]
                    if priority <= existing_priority:
                        logger.debug(
                            f"参数 {param} 的即时设置被拒绝，因为已存在一个优先级为 "
                            f"{existing_priority} 的缓动 (新请求优先级: {priority}).",
                        )
                        return
                    logger.debug(
                        f"参数 {param} 的即时设置正在中断一个优先级为 {existing_priority} 的缓动 (新请求优先级: {priority}).",
                    )
                    del self._active_tweens[param]

                self.controlled_params[param] = end
            await self._plugin.set_parameter_value(param, end, mode=mode)
            return

        loop = asyncio.get_event_loop()
        start_time = loop.time()
        steps = max(1, int(duration * fps))
        interval = duration / steps

        async with self._lock:
            if param in self._active_tweens:
                _existing_task, existing_priority = self._active_tweens[param]
                if priority <= existing_priority:
                    logger.debug(
                        f"参数 {param} 的缓动被拒绝，因为已存在一个优先级为 "
                        f"{existing_priority} 的缓动在运行 (新请求优先级: {priority}).",
                    )
                    return
                logger.debug(
                    f"参数 {param} 的缓动中断了另一个优先级为 {existing_priority} 的任务，并以新的优先级 {priority} 接管.",
                )

            self._active_tweens[param] = (current_task, priority)

        try:
            for step in range(steps):
                t = (step + 1) / steps
                value = start + (end - start) * easing_func(t)

                should_set_value = False
                async with self._lock:
                    active_task_tuple = self._active_tweens.get(param)
                    if active_task_tuple and active_task_tuple[0] is current_task:
                        self.controlled_params[param] = value
                        should_set_value = True

                if should_set_value:
                    await self._plugin.set_parameter_value(param, value, mode=mode)

                now = loop.time()
                next_time = start_time + (step + 1) * interval
                sleep_time = next_time - now
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            logger.debug(f"参数 {param} 的缓动任务被取消.")
            raise  # 重新抛出异常以确保外部调用者知道它被取消了
        finally:
            async with self._lock:
                # 仅当此任务仍是活动任务时才移除
                if param in self._active_tweens:
                    active_task, _ = self._active_tweens[param]
                    if active_task is current_task:
                        del self._active_tweens[param]

    def release_all(self):
        """释放所有参数的控制权。"""
        self.controlled_params.clear()
        logger.info("已释放所有 Tweener 控制的参数.")

    @staticmethod
    def random_easing():
        """随机从常用缓动函数中选择一个，按权重分布。"""
        funcs = [
            Easing.in_out_sine,
            Easing.in_out_quad,
            Easing.in_out_back,
        ]
        weights = [0.75, 0.15, 0.1]
        return random.choices(funcs, weights=weights)[0]


# 创建一个全局单例
tweener = Tweener()
