import asyncio
import random
from typing import Optional, Type

from pydantic import Field
from services.tweener import tweener
from utils.easing import Easing
from utils.logger import logger

from configs.base import ConfigBase

from .base_controller import OneShotController


class MouthExpressionConfig(ConfigBase):
    """嘴部表情配置"""

    ENABLED: bool = Field(default=True, description="是否启用嘴部表情变化")
    OPEN_MIN: float = Field(default=0.0, description="嘴巴开合最小值（闭合）")
    OPEN_MAX: float = Field(default=0.7, description="嘴巴开合最大值（张开，可调小避免过度张嘴）")
    OPEN_PARAMETER: str = Field(default="MouthOpen", description="嘴巴开合控制的参数名")
    LOUDNESS_THRESHOLD: float = Field(default=-30, description="响度阈值(LUFS)")


class MouthSyncController(OneShotController[MouthExpressionConfig]):
    """根据音频响度控制嘴部开合的控制器"""

    @classmethod
    def get_config_class(cls) -> Type[MouthExpressionConfig]:
        return MouthExpressionConfig

    @classmethod
    def get_config_filename(cls) -> str:
        return "mouth_sync.yaml"

    async def execute(self, loudness_queue: asyncio.Queue[Optional[float]]):
        if not self.config.ENABLED:
            return

        logger.info("启动嘴型同步...")
        try:
            while True:
                lufs = await loudness_queue.get()
                logger.info(f"响度: {lufs}")
                if lufs is None:  # End of stream
                    break

                target_open = self.config.OPEN_MIN
                if lufs >= self.config.LOUDNESS_THRESHOLD:
                    target_open = random.uniform(self.config.OPEN_MIN, self.config.OPEN_MAX)

                await tweener.tween(
                    param=self.config.OPEN_PARAMETER,
                    end=target_open,
                    duration=0.05, #0.06 0.07都会提前结束
                    easing_func=Easing.linear,
                    priority=2,  # 高优先级以覆盖其他可能影响嘴部的动画
                )
                await asyncio.sleep(0.05)

        except asyncio.CancelledError:
            logger.info("嘴型同步任务被取消.")
        finally:
            logger.info("嘴型同步结束, 闭合嘴巴.")
            await tweener.tween(
                param=self.config.OPEN_PARAMETER,
                end=self.config.OPEN_MIN,
                duration=0.2,
                easing_func=Easing.out_quad,
                priority=2,
            )


mouth_sync_controller = MouthSyncController()
