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
        self._current_value = tweener.controlled_params.get(self.cfg.PARAMETER, 0.0)

    async def run_cycle(self):
        """执行一次呼吸周期：吸气 -> 呼气"""
        try:
            # 吸气
            await tweener.tween(
                self.cfg.PARAMETER,
                self._current_value,
                self.cfg.MAX_VALUE,
                self.cfg.INHALE_DURATION,
                Easing.in_out_sine,
            )
            self._current_value = self.cfg.MAX_VALUE

            # 呼气
            await tweener.tween(
                self.cfg.PARAMETER,
                self._current_value,
                self.cfg.MIN_VALUE,
                self.cfg.EXHALE_DURATION,
                Easing.in_out_sine,
            )
            self._current_value = self.cfg.MIN_VALUE
        except asyncio.CancelledError:
            raise
