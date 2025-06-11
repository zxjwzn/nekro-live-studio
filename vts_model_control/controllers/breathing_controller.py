import asyncio
import random
from typing import Type

from configs.base import ConfigBase
from pydantic import Field
from services.tweener import tweener
from utils.easing import Easing
from utils.logger import logger

from .base_controller import BaseController


class BreathingConfig(ConfigBase):
    """呼吸配置"""

    ENABLED: bool = Field(default=True, description="是否启用呼吸效果")
    MIN_VALUE: float = Field(default=-3.0, description="呼吸参数最小值（呼气）")
    MAX_VALUE: float = Field(default=3.0, description="呼吸参数最大值（吸气）")
    INHALE_DURATION: float = Field(default=1.0, description="吸气持续时间（秒）")
    EXHALE_DURATION: float = Field(default=2.0, description="呼气持续时间（秒）")
    PARAMETER: str = Field(default="FaceAngleY", description="呼吸控制的参数名")


class BreathingController(BaseController[BreathingConfig]):
    """呼吸控制器，通过缓动 FaceAngleY 参数实现模拟呼吸的效果。"""

    @classmethod
    def get_config_class(cls) -> Type[BreathingConfig]:
        return BreathingConfig

    @classmethod
    def get_config_filename(cls) -> str:
        return "breathing.yaml"

    def __init__(self):
        super().__init__()
        self.is_idle_animation = True

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
