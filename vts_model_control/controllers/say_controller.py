import asyncio
import audioop
from typing import Optional, Type

from configs.base import ConfigBase
from pydantic import Field
from services.tweener import tweener
from utils.easing import Easing
from utils.logger import logger

from .base_controller import BaseController


class SayConfig(ConfigBase):
    """语音驱动嘴形配置"""

    ENABLED: bool = Field(default=True, description="是否启用语音驱动嘴形")
    MOUTH_OPEN_PARAMETER: str = Field(default="MouthOpen", description="嘴巴开合控制的参数名")
    LOUDNESS_THRESHOLD: float = Field(default=0.01, description="响度阈值，低于此值时嘴巴趋于闭合")
    LOUDNESS_SENSITIVITY: float = Field(default=2.0, description="响度敏感度，响度到嘴部开合的映射乘数")
    SMOOTHING_FACTOR: float = Field(default=0.3, description="嘴部开合平滑系数 (0-1, 越小越平滑)")


class SayController(BaseController[SayConfig]):
    """
    通过分析 TTS 音频流的响度来控制嘴部开合。
    """

    @classmethod
    def get_config_class(cls) -> Type[SayConfig]:
        return SayConfig

    @classmethod
    def get_config_filename(cls) -> str:
        return "say.yaml"

    def __init__(self):
        super().__init__()
        self.is_idle_animation = False
        self.audio_queue: Optional[asyncio.Queue[Optional[bytes]]] = None
        self._current_mouth_open = 0.0

    def prepare_to_speak(self, audio_queue: asyncio.Queue[Optional[bytes]]):
        """在说话前准备，设置音频队列。"""
        self.audio_queue = audio_queue
        self._current_mouth_open = 0.0

    async def _run(self):
        """
        控制器主循环，处理音频流并控制嘴部。
        此方法由 controller_manager 启动。
        """
        if not self.audio_queue:
            logger.error("SayController: audio_queue 未在运行前设置。")
            return

        try:
            while self.is_running:
                # 从队列中获取原始 PCM 音频块
                pcm_chunk = await self.audio_queue.get()
                if pcm_chunk is None:  # 接收到结束信号
                    break

                rms = audioop.rms(pcm_chunk, 2)  # 2 表示样本宽度为 2 字节 (16-bit)
                normalized_rms = rms / 32767
                target_mouth_open = 0.0
                if normalized_rms > self.config.LOUDNESS_THRESHOLD:
                    target_mouth_open = min(
                        1.0,
                        (normalized_rms - self.config.LOUDNESS_THRESHOLD)
                        * self.config.LOUDNESS_SENSITIVITY,
                    )

                self._current_mouth_open = (
                    self.config.SMOOTHING_FACTOR * target_mouth_open
                    + (1 - self.config.SMOOTHING_FACTOR) * self._current_mouth_open
                )

                await tweener.tween(
                    param=self.config.MOUTH_OPEN_PARAMETER,
                    end=self._current_mouth_open,
                    duration=0,
                    easing_func=Easing.linear,
                    priority=2,
                )
        except Exception as e:
            logger.error(f"SayController 运行循环中发生错误: {e}", exc_info=True)
        finally:
            logger.info("SayController 运行结束，关闭嘴部。")
            await tweener.tween(
                param=self.config.MOUTH_OPEN_PARAMETER,
                end=0.0,
                duration=0.2,
                easing_func=Easing.linear,
                priority=2,
            )
            self._current_mouth_open = 0.0
            self.audio_queue = None

    async def run_cycle(self):
        pass
