import asyncio
import random

from configs.config import config
from utils.easing import Easing
from utils.logger import logger
from services.tweener import tweener

from .base_controller import BaseController


class BreathingController(BaseController):
    """呼吸控制器，通过缓动 FaceAngleY 参数实现模拟呼吸的效果。"""

    def __init__(self):
        super().__init__()
        self.cfg = config.BREATHING
        self.skip_pause = True

    async def run_cycle(self):
        """执行一次呼吸周期：吸气 -> 呼气"""
        try:
            # 吸气
            await tweener.tween(
                param=self.cfg.PARAMETER,
                end=self.cfg.MAX_VALUE,
                duration=self.cfg.INHALE_DURATION,
                easing_func=Easing.in_out_sine,
            )

            # 呼气
            await tweener.tween(
                param=self.cfg.PARAMETER,
                end=self.cfg.MIN_VALUE,
                duration=self.cfg.EXHALE_DURATION,
                easing_func=Easing.in_out_sine,
            )
        except asyncio.CancelledError:
            raise
