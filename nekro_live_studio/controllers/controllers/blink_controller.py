import asyncio
import random
from typing import Type

from ...services.tweener import tweener
from ...utils.easing import Easing
from ...utils.logger import logger
from ..base_controller import IdleController
from ..config import BlinkConfig
from ..config_manager import config_manager


class BlinkController(IdleController[BlinkConfig]):
    """眨眼控制器，使用 Tweener 实现闭眼-睁眼过渡循环"""

    @property
    def config(self) -> BlinkConfig:
        return config_manager.config.blink

    async def run_cycle(self):
        """执行一次眨眼周期: 在 tween/closed_hold/open 阶段完成眨眼，等待阶段可被取消"""
        # 闭眼
        await asyncio.gather(
            tweener.tween(
                param=self.config.LEFT_PARAMETER,
                end=self.config.MIN_VALUE,
                duration=self.config.CLOSE_DURATION,
                easing_func=Easing.out_sine,
            ),
            tweener.tween(
                param=self.config.RIGHT_PARAMETER,
                end=self.config.MIN_VALUE,
                duration=self.config.CLOSE_DURATION,
                easing_func=Easing.out_sine,
            ),
        )
        # 保持闭眼
        await asyncio.sleep(self.config.CLOSED_HOLD)
        # 睁眼
        await asyncio.gather(
            tweener.tween(
                param=self.config.LEFT_PARAMETER,
                end=self.config.MAX_VALUE,
                duration=self.config.OPEN_DURATION,
                easing_func=Easing.in_sine,
            ),
            tweener.tween(
                param=self.config.RIGHT_PARAMETER,
                end=self.config.MAX_VALUE,
                duration=self.config.OPEN_DURATION,
                easing_func=Easing.in_sine,
            ),
        )

        # 如果外部 stop 事件已设置，退出本周期
        if self._stop_event.is_set():
            return
        # 随机等待下一次眨眼，睡眠阶段可被取消立即退出
        wait_time = random.uniform(self.config.MIN_INTERVAL, self.config.MAX_INTERVAL)
        logger.debug(f"下次眨眼等待: {wait_time:.2f} 秒")
        try:
            await asyncio.sleep(wait_time)
        except asyncio.CancelledError:
            # 在等待阶段取消，则退出
            return
