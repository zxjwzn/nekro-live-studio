import asyncio
import random
from typing import Type

from pydantic import Field

from ..configs.base import ConfigBase
from ..services.tweener import tweener
from ..utils.easing import Easing
from ..utils.logger import logger
from .base_controller import IdleController


class BlinkConfig(ConfigBase):
    """眨眼配置"""

    ENABLED: bool = Field(default=True, description="是否启用眨眼效果")
    MIN_INTERVAL: float = Field(
        default=2.0,
        description="两次眨眼之间的最小间隔时间（秒）",
    )
    MAX_INTERVAL: float = Field(
        default=4.0,
        description="两次眨眼之间的最大间隔时间（秒）",
    )
    CLOSE_DURATION: float = Field(default=0.15, description="闭眼动画持续时间（秒）")
    OPEN_DURATION: float = Field(default=0.3, description="睁眼动画持续时间（秒）")
    CLOSED_HOLD: float = Field(default=0.05, description="眼睛闭合状态的保持时间（秒）")
    LEFT_PARAMETER: str = Field(default="EyeOpenLeft", description="眨眼控制的参数名")
    RIGHT_PARAMETER: str = Field(default="EyeOpenRight", description="眨眼控制的参数名")
    MIN_VALUE: float = Field(default=0.0, description="眨眼最小值（闭眼）")
    MAX_VALUE: float = Field(default=1, description="眨眼最大值（睁眼）")


class BlinkController(IdleController[BlinkConfig]):
    """眨眼控制器，使用 Tweener 实现闭眼-睁眼过渡循环"""

    @classmethod
    def get_config_class(cls) -> Type[BlinkConfig]:
        return BlinkConfig

    @classmethod
    def get_config_filename(cls) -> str:
        return "blink.yaml"

    def __init__(self):
        super().__init__()

    async def run_cycle(self):
        """执行一次眨眼周期: 在 tween/closed_hold/open 阶段完成眨眼，等待阶段可被取消"""
        # 闭眼
        await asyncio.gather(
            tweener.tween(
                param=self.config.LEFT_PARAMETER,
                end=self.config.MIN_VALUE,
                duration=self.config.CLOSE_DURATION,
                easing_func=Easing.out_sine,
            ),
            tweener.tween(
                param=self.config.RIGHT_PARAMETER,
                end=self.config.MIN_VALUE,
                duration=self.config.CLOSE_DURATION,
                easing_func=Easing.out_sine,
            ),
        )
        # 保持闭眼
        await asyncio.sleep(self.config.CLOSED_HOLD)
        # 睁眼
        await asyncio.gather(
            tweener.tween(
                param=self.config.LEFT_PARAMETER,
                end=self.config.MAX_VALUE,
                duration=self.config.OPEN_DURATION,
                easing_func=Easing.in_sine,
            ),
            tweener.tween(
                param=self.config.RIGHT_PARAMETER,
                end=self.config.MAX_VALUE,
                duration=self.config.OPEN_DURATION,
                easing_func=Easing.in_sine,
            ),
        )

        # 如果外部 stop 事件已设置，退出本周期
        if self._stop_event.is_set():
            return
        # 随机等待下一次眨眼，睡眠阶段可被取消立即退出
        wait_time = random.uniform(self.config.MIN_INTERVAL, self.config.MAX_INTERVAL)
        logger.debug(f"下次眨眼等待: {wait_time:.2f} 秒")
        try:
            await asyncio.sleep(wait_time)
        except asyncio.CancelledError:
            # 在等待阶段取消，则退出
            return
