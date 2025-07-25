import asyncio
import random
from typing import Type

from ...services.tweener import tweener
from ...utils.easing import Easing
from ...utils.logger import logger
from ..base_controller import IdleController
from ..config import MouthExpressionConfig
from ..config_manager import config_manager


class MouthExpressionController(IdleController[MouthExpressionConfig]):
    """嘴部表情控制器，随机改变微笑和嘴巴张开程度，增加生动性。"""

    @property
    def config(self) -> MouthExpressionConfig:
        return config_manager.config.mouth_expression

    async def run_cycle(self):
        """执行一次嘴部表情变化周期。"""
        target_smile = random.uniform(self.config.SMILE_MIN, self.config.SMILE_MAX)
        target_open = random.uniform(self.config.OPEN_MIN, self.config.OPEN_MAX)
        duration = random.uniform(self.config.CHANGE_MIN_DURATION, self.config.CHANGE_MAX_DURATION)
        easing_func = tweener.random_easing()
        logger.debug(
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
