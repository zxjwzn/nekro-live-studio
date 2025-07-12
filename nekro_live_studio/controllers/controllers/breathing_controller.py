import asyncio
import random
from typing import Type

from pydantic import Field

from ...services.tweener import tweener
from ...utils.easing import Easing
from ...utils.logger import logger
from ..base_controller import IdleController
from ..config import BreathingConfig
from ..config_manager import config_manager


class BreathingController(IdleController[BreathingConfig]):
    """呼吸控制器，通过缓动 FaceAngleY 参数实现模拟呼吸的效果。"""

    @property
    def config(self) -> BreathingConfig:
        return config_manager.config.breathing

    async def run_cycle(self):
        """执行一次呼吸周期：吸气 -> 呼气"""
        # 吸气
        await tweener.tween(
            param=self.config.PARAMETER,
            end=self.config.MAX_VALUE,
            duration=self.config.INHALE_DURATION,
            easing_func=Easing.in_out_sine,
        )

        # 呼气
        await tweener.tween(
            param=self.config.PARAMETER,
            end=self.config.MIN_VALUE,
            duration=self.config.EXHALE_DURATION,
            easing_func=Easing.in_out_sine,
        )
