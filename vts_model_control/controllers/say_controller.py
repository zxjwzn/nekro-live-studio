import asyncio
import random
from typing import Type

from configs.base import ConfigBase
from pydantic import Field
from services.tweener import tweener
from utils.easing import Easing
from utils.logger import logger

from .base_controller import BaseController


class SayConfig(ConfigBase):
    """嘴部表情配置"""

    ENABLED: bool = Field(default=True, description="是否启用嘴部表情变化")
    SMILE_MIN: float = Field(default=0.3, description="嘴角微笑最小值（不高兴）")
    SMILE_MAX: float = Field(default=0.7, description="嘴角微笑最大值（高兴）")
    OPEN_MIN: float = Field(default=0.3, description="嘴巴开合最小值（闭合）")
    OPEN_MAX: float = Field(default=0.7, description="嘴巴开合最大值（张开，可调小避免过度张嘴）")
    SMILE_PARAMETER: str = Field(default="MouthSmile", description="嘴角微笑控制的参数名")
    OPEN_PARAMETER: str = Field(default="MouthOpen", description="嘴巴开合控制的参数名")
    SMOOTHING_UP: float = Field(default=0.05, description="口型张开平滑时间（秒）")
    SMOOTHING_DOWN: float = Field(default=0.05, description="口型闭合平滑时间（秒）")


class SayController(BaseController[SayConfig]):
    """模拟说话时快速开合嘴部的控制器。"""

    @classmethod
    def get_config_class(cls) -> Type[SayConfig]:
        return SayConfig

    @classmethod
    def get_config_filename(cls) -> str:
        return "say.yaml"

    def __init__(self):
        super().__init__()
        self.is_idle_animation = False

    async def run_cycle(self):
        """执行一次开合嘴的动画，并随机改变微笑程度。"""
        # 随机选择一个张嘴程度
        target_open = random.uniform(self.config.OPEN_MIN, self.config.OPEN_MAX)
        # 随机选择一个微笑程度
        target_smile = random.uniform(self.config.SMILE_MIN, self.config.SMILE_MAX)

        # 张嘴并同时调整微笑
        await asyncio.gather(
            tweener.tween(
                param=self.config.OPEN_PARAMETER,
                end=target_open,
                duration=self.config.SMOOTHING_UP,
                easing_func=Easing.out_sine,
            ),
            tweener.tween(
                param=self.config.SMILE_PARAMETER,
                end=target_smile,
                duration=self.config.SMOOTHING_UP,
                easing_func=Easing.out_sine,
            ),
        )

        # 闭嘴。微笑状态会由 MouthExpressionController 或下一次 run_cycle 改变
        await tweener.tween(
            param=self.config.OPEN_PARAMETER,
            end=self.config.OPEN_MIN,
            duration=self.config.SMOOTHING_DOWN,
            easing_func=Easing.in_sine,
        )
        
