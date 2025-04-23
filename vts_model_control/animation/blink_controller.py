import asyncio
import random
from config import config
from animation.tweener import Tweener
from animation.easing import Easing
from utils.logger import logger

class BlinkController:
    """眨眼控制器，使用 Tweener 实现闭眼-睁眼过渡循环"""
    def __init__(self, plugin):
        self.plugin = plugin
        self.cfg = config.blink
        self._stop_event = asyncio.Event()
        self._task = None

    async def start(self):
        """启动眨眼循环"""
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self):
        """停止眨眼循环"""
        self._stop_event.set()
        if self._task:
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self):
        while not self._stop_event.is_set():
            logger.info("开始眨眼周期")
            # 随机等待下一次眨眼
            wait_time = random.uniform(self.cfg.MIN_INTERVAL, self.cfg.MAX_INTERVAL)
            logger.info(f"下次眨眼等待: {wait_time:.2f} 秒")
            try:
                await asyncio.wait_for(asyncio.sleep(wait_time), timeout=wait_time + 1)
            except asyncio.TimeoutError:
                pass

            if self._stop_event.is_set():
                break

            # 闭眼
            logger.info(f"开始闭眼 (缓动 {self.cfg.MAX_VALUE:.2f} -> {self.cfg.MIN_VALUE:.2f})")
            await asyncio.gather(
                Tweener.tween(
                    self.plugin,
                    self.cfg.LEFT_PARAMETER,
                self.cfg.MAX_VALUE,
                self.cfg.MIN_VALUE,
                self.cfg.CLOSE_DURATION,
                    Easing.ease_out_sine
                ),
                Tweener.tween(
                    self.plugin,
                    self.cfg.RIGHT_PARAMETER,
                    self.cfg.MAX_VALUE,
                    self.cfg.MIN_VALUE,
                    self.cfg.CLOSE_DURATION,
                    Easing.ease_out_sine
                ),
            )

            # 保持闭眼
            logger.info(f"保持闭眼 {self.cfg.CLOSED_HOLD:.2f} 秒")
            await asyncio.sleep(self.cfg.CLOSED_HOLD)

            # 睁眼
            logger.info(f"开始睁眼 (缓动 {self.cfg.MIN_VALUE:.2f} -> {self.cfg.MAX_VALUE:.2f})")
            await asyncio.gather(
                Tweener.tween(
                    self.plugin,
                    self.cfg.LEFT_PARAMETER,
                    self.cfg.MIN_VALUE,
                    self.cfg.MAX_VALUE,
                    self.cfg.OPEN_DURATION,
                    Easing.ease_in_sine
                ),
                Tweener.tween(
                    self.plugin,
                    self.cfg.RIGHT_PARAMETER,
                    self.cfg.MIN_VALUE,
                    self.cfg.MAX_VALUE,
                    self.cfg.OPEN_DURATION,
                    Easing.ease_in_sine
                ),
            )

            # 确保最终睁眼
            await asyncio.gather(
                self.plugin.set_parameter_value(self.cfg.LEFT_PARAMETER, self.cfg.MAX_VALUE, mode="set"),
                self.plugin.set_parameter_value(self.cfg.RIGHT_PARAMETER, self.cfg.MAX_VALUE, mode="set")
            )
            logger.info("眨眼动画完成，确保眼睛保持睁开")
            logger.info("眼睛状态已最终设置为睁开")

            # 随机等待下一次眨眼
            wait_time = random.uniform(self.cfg.MIN_INTERVAL, self.cfg.MAX_INTERVAL)
            logger.info(f"下次眨眼等待: {wait_time:.2f} 秒")
            try:
                await asyncio.wait_for(asyncio.sleep(wait_time), timeout=wait_time + 1)
            except asyncio.TimeoutError:
                pass