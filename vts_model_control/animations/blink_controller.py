import asyncio
import random

from configs.config import config
from services.tweener import tweener
from utils.easing import Easing
from utils.logger import logger

from .base_controller import BaseController


class BlinkController(BaseController):
    """眨眼控制器，使用 Tweener 实现闭眼-睁眼过渡循环"""

    def __init__(self):
        super().__init__()
        self.cfg = config.BLINK
        self.skip_pause = False

    async def run_cycle(self):
        """执行一次眨眼周期: 在 tween/closed_hold/open 阶段完成眨眼，等待阶段可被取消"""
        try:
            # 闭眼
            await asyncio.gather(
                tweener.tween(
                    param=self.cfg.LEFT_PARAMETER,
                    end=self.cfg.MIN_VALUE,
                    duration=self.cfg.CLOSE_DURATION,
                    easing_func=Easing.out_sine,
                ),
                tweener.tween(
                    param=self.cfg.RIGHT_PARAMETER,
                    end=self.cfg.MIN_VALUE,
                    duration=self.cfg.CLOSE_DURATION,
                    easing_func=Easing.out_sine,
                ),
            )
            # 保持闭眼
            await asyncio.sleep(self.cfg.CLOSED_HOLD)
            # 睁眼
            await asyncio.gather(
                tweener.tween(
                    param=self.cfg.LEFT_PARAMETER,
                    end=self.cfg.MAX_VALUE,
                    duration=self.cfg.OPEN_DURATION,
                    easing_func=Easing.in_sine,
                ),
                tweener.tween(
                    param=self.cfg.RIGHT_PARAMETER,
                    end=self.cfg.MAX_VALUE,
                    duration=self.cfg.OPEN_DURATION,
                    easing_func=Easing.in_sine,
                ),
            )
        except asyncio.CancelledError:
            raise

        # 如果外部 stop 事件已设置，退出本周期
        if self._stop_event.is_set():
            return
        # 随机等待下一次眨眼，睡眠阶段可被取消立即退出
        wait_time = random.uniform(self.cfg.MIN_INTERVAL, self.cfg.MAX_INTERVAL)
        logger.debug(f"下次眨眼等待: {wait_time:.2f} 秒")
        try:
            await asyncio.sleep(wait_time)
        except asyncio.CancelledError:
            # 在等待阶段取消，则退出
            return
