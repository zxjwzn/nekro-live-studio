import asyncio
import random
from typing import Type

from pydantic import Field
from services.tweener import tweener
from utils.easing import Easing
from utils.logger import logger

from configs.base import ConfigBase

from .base_controller import OneShotController


class MouthExpressionConfig(ConfigBase):
    """嘴部表情配置"""

    ENABLED: bool = Field(default=True, description="是否启用嘴部表情变化")
    OPEN_MIN: float = Field(default=0.1, description="嘴巴开合最小值（闭合）")
    OPEN_MAX: float = Field(default=0.7, description="嘴巴开合最大值（张开，可调小避免过度张嘴）")
    OPEN_PARAMETER: str = Field(default="MouthOpen", description="嘴巴开合控制的参数名")
    LOUDNESS_THRESHOLD_MIN: float = Field(default=-10, description="响度最小值(dB)")
    LOUDNESS_THRESHOLD_MAX: float = Field(default=10, description="响度最大值(dB)")


class MouthSyncController(OneShotController[MouthExpressionConfig]):
    """嘴部表情控制器，随机改变微笑和嘴巴张开程度，增加生动性。"""

    @classmethod
    def get_config_class(cls) -> Type[MouthExpressionConfig]:
        return MouthExpressionConfig

    @classmethod
    def get_config_filename(cls) -> str:
        return "mouth_sync.yaml"

    def __init__(self):
        super().__init__()

    async def execute(self, loudness: float, duration: float):
        if not self.config.ENABLED:
            return

        if loudness < self.config.LOUDNESS_THRESHOLD_MIN or loudness > self.config.LOUDNESS_THRESHOLD_MAX:
            return
        
        # 将响度线性映射到嘴巴张开程度
        # 计算响度在阈值范围内的相对位置（0-1）
        loudness_ratio = (loudness - self.config.LOUDNESS_THRESHOLD_MIN) / (
            self.config.LOUDNESS_THRESHOLD_MAX - self.config.LOUDNESS_THRESHOLD_MIN
        )
        
        # 将比例映射到嘴巴张开范围
        mouth_open = self.config.OPEN_MIN + loudness_ratio * (self.config.OPEN_MAX - self.config.OPEN_MIN)
        
        # 确保值在有效范围内
        mouth_open = max(self.config.OPEN_MIN, min(self.config.OPEN_MAX, mouth_open))

        asyncio.gather(
            tweener.tween(
                self.config.OPEN_PARAMETER,
                mouth_open,
                duration,
                Easing.out_sine,
                2,
            ),
        )
