import asyncio
import random

from configs.config import config
from utils.easing import Easing
from utils.logger import logger
from services.tweener import tweener

from .base_controller import BaseController


class MouthExpressionController(BaseController):
    """嘴部表情控制器，随机改变微笑和嘴巴张开程度，增加生动性。"""

    def __init__(self):
        super().__init__()
        self.cfg = config.MOUTH_EXPRESSION
        self._current_smile = tweener.controlled_params.get(self.cfg.SMILE_PARAMETER, 0.0)
        self._current_open = tweener.controlled_params.get(self.cfg.OPEN_PARAMETER, 0.0)

    async def run_cycle(self):
        """执行一次嘴部表情变化周期。"""
        target_smile = random.uniform(self.cfg.SMILE_MIN, self.cfg.SMILE_MAX)
        target_open = random.uniform(self.cfg.OPEN_MIN, self.cfg.OPEN_MAX)
        duration = random.uniform(self.cfg.CHANGE_MIN_DURATION, self.cfg.CHANGE_MAX_DURATION)
        easing_func = tweener.random_easing()

        try:
            logger.info(
                f"嘴部表情: "
                f"Smile: {self._current_smile:.2f} -> {target_smile:.2f}, "
                f"Open: {self._current_open:.2f} -> {target_open:.2f}, "
                f"时长: {duration:.2f}s, 缓动: {easing_func.__name__}"
            )
            await asyncio.gather(
                tweener.tween(self.cfg.SMILE_PARAMETER, self._current_smile, target_smile, duration, easing_func),
                tweener.tween(self.cfg.OPEN_PARAMETER, self._current_open, target_open, duration, easing_func),
            )
            self._current_smile = target_smile
            self._current_open = target_open
        except asyncio.CancelledError:
            raise
