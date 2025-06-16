import asyncio
import random
from typing import Type

from pydantic import Field
from services.tweener import tweener
from utils.easing import Easing
from utils.logger import logger

from configs.base import ConfigBase

from .base_controller import IdleController


class MouthExpressionConfig(ConfigBase):
    """嘴部表情配置"""

    ENABLED: bool = Field(default=True, description="是否启用嘴部表情变化")
    SMILE_MIN: float = Field(default=0.1, description="嘴角微笑最小值（不高兴）")
    SMILE_MAX: float = Field(default=0.7, description="嘴角微笑最大值（高兴）")
    OPEN_MIN: float = Field(default=0.1, description="嘴巴开合最小值（闭合）")
    OPEN_MAX: float = Field(default=0.7, description="嘴巴开合最大值（张开，可调小避免过度张嘴）")
    CHANGE_MIN_DURATION: float = Field(default=2.0, description="表情变化最短持续时间（秒）")
    CHANGE_MAX_DURATION: float = Field(default=7.0, description="表情变化最长持续时间（秒）")
    SMILE_PARAMETER: str = Field(default="MouthSmile", description="嘴角微笑控制的参数名")
    OPEN_PARAMETER: str = Field(default="MouthOpen", description="嘴巴开合控制的参数名")


class MouthExpressionController(IdleController[MouthExpressionConfig]):
    """嘴部表情控制器，随机改变微笑和嘴巴张开程度，增加生动性。"""

    @classmethod
    def get_config_class(cls) -> Type[MouthExpressionConfig]:
        return MouthExpressionConfig

    @classmethod
    def get_config_filename(cls) -> str:
        return "mouth_expression.yaml"

    def __init__(self):
        super().__init__()

    async def run_cycle(self):
        """执行一次嘴部表情变化周期。"""
        target_smile = random.uniform(self.config.SMILE_MIN, self.config.SMILE_MAX)
        target_open = random.uniform(self.config.OPEN_MIN, self.config.OPEN_MAX)
        duration = random.uniform(self.config.CHANGE_MIN_DURATION, self.config.CHANGE_MAX_DURATION)
        easing_func = tweener.random_easing()
        logger.info(
            f"嘴部表情: "
            f"Smile: {target_smile:.2f}, "
            f"Open: {target_open:.2f}, "
            f"时长: {duration:.2f}s, 缓动: {easing_func.__name__}",
        )
        await asyncio.gather(
            tweener.tween(
                param=self.config.SMILE_PARAMETER,
                end=target_smile,
                duration=duration,
                easing_func=easing_func,
            ),
            tweener.tween(
                param=self.config.OPEN_PARAMETER,
                end=target_open,
                duration=duration,
                easing_func=easing_func,
            ),
        )
