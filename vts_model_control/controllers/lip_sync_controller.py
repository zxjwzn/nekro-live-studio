import asyncio
import audioop
from typing import Type

from controllers.base_controller import BaseController
from pydantic import Field
from services.tweener import tweener
from utils.easing import Easing
from utils.logger import logger

from configs.base import ConfigBase


class LipSyncConfig(ConfigBase):
    """口型同步配置"""

    ENABLED: bool = Field(default=True, description="是否启用口型同步")
    MOUTH_OPEN_PARAMETER: str = Field(default="MouthOpen", description="嘴巴开合控制的参数名")
    MIN_LOUDNESS: int = Field(default=200, description="识别为声音的最小响度阈值 (RMS)")
    MAX_LOUDNESS: int = Field(default=10000, description="映射到最大嘴型的响度 (RMS)")
    SMOOTHING_FACTOR: float = Field(default=0.6, description="嘴部动作平滑因子 (0-1, 越大越平滑)")
    TWEEN_DURATION: float = Field(default=0.08, description="每次嘴部变化的缓动时间 (秒)")
    AUDIO_SAMPLE_WIDTH: int = Field(default=2, description="音频采样宽度 (bytes, 16-bit a-law is 2)")
    AUDIO_CHANNELS: int = Field(default=1, description="音频通道数")


class LipSyncController(BaseController[LipSyncConfig]):
    """嘴部表情控制器，随机改变微笑和嘴巴张开程度，增加生动性。"""

    @classmethod
    def get_config_class(cls) -> Type[LipSyncConfig]:
        return LipSyncConfig

    @classmethod
    def get_config_filename(cls) -> str:
        return "lip_sync.yaml"

    def __init__(self):
        super().__init__()
        self.is_idle_animation = False
        self._smoothed_loudness: float = 0.0

    def _calculate_target_open(self, chunk: bytes) -> float:
        """根据音频块计算目标嘴部开度"""
        try:
            loudness = audioop.rms(chunk, self.config.AUDIO_SAMPLE_WIDTH)
        except audioop.error as e:
            # 当 chunk 为空或长度不为采样宽度的倍数时，会发生此错误
            logger.debug(f"无法计算音频响度: {e}")
            return 0.0

        # 平滑处理
        self._smoothed_loudness = (
            self._smoothed_loudness * self.config.SMOOTHING_FACTOR
            + loudness * (1 - self.config.SMOOTHING_FACTOR)
        )

        if self._smoothed_loudness < self.config.MIN_LOUDNESS:
            return 0.0

        # 归一化到 0-1
        denominator = self.config.MAX_LOUDNESS - self.config.MIN_LOUDNESS
        if denominator <= 0:
            return 1.0 if self._smoothed_loudness >= self.config.MIN_LOUDNESS else 0.0

        clamped_loudness = min(self._smoothed_loudness, self.config.MAX_LOUDNESS)
        return (clamped_loudness - self.config.MIN_LOUDNESS) / denominator

    async def process_chunk(self, chunk: bytes):
        """处理单个音频块并更新嘴部参数。"""
        if not self.config.ENABLED:
            return
        target_open = self._calculate_target_open(chunk)
        await tweener.tween(
            param=self.config.MOUTH_OPEN_PARAMETER,
            end=target_open,
            duration=self.config.TWEEN_DURATION,
            priority=2,
            easing_func=Easing.out_sine,  # 线性缓动
        )

    async def stop(self):
        """平滑地关闭嘴巴。"""
        if not self.config.ENABLED:
            return
        logger.info("音频播放结束，关闭嘴巴")
        self._smoothed_loudness = 0.0
        await tweener.tween(
            param=self.config.MOUTH_OPEN_PARAMETER,
            end=0.0,
            duration=0.2,
            priority=2,
            easing_func=Easing.out_sine,
        )

    async def run_cycle(self):
        pass
