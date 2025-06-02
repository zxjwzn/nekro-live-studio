import asyncio
import random
from configs.config import config
from services.tweener import Tweener
from utils.easing import Easing
from utils.logger import logger
from .base_controller import BaseController
from typing import List


class MouthExpressionController(BaseController):
    """嘴部表情控制器，使用 Tweener 实现随机嘴部表情变化循环"""

    def __init__(self):
        super().__init__()
        self.cfg = config.mouth_expression
        # 当前表情状态
        self._current_smile = 0.0
        self._current_open = 0.0
        self.skip_pause = False

    async def run_cycle(self):
        """执行一次嘴部表情随机过渡"""
        # 随机生成新表情目标
        easing_func = Tweener.random_easing()
        new_smile = random.uniform(self.cfg.smile_min, self.cfg.smile_max)
        new_open = random.uniform(self.cfg.open_min, self.cfg.open_max)
        duration = random.uniform(
            self.cfg.change_min_duration, self.cfg.change_max_duration
        )
        logger.info(
            f"随机表情参数: 当前表情=(微笑:{self._current_smile:.2f}, 开口:{self._current_open:.2f}), "
            f"目标=(微笑:{new_smile:.2f}, 开口:{new_open:.2f}), 持续时间={duration:.2f}s, 缓动函数={easing_func.__name__}"
        )
        # 并行动画过渡
        await asyncio.gather(
            Tweener.tween(
                self.plugin,
                self.cfg.smile_parameter,
                self._current_smile,
                new_smile,
                duration,
                easing_func,
            ),
            Tweener.tween(
                self.plugin,
                self.cfg.open_parameter,
                self._current_open,
                new_open,
                duration,
                easing_func,
            ),
        )
        # 确保最终状态
        await asyncio.gather(
            self.plugin.set_parameter_value(
                self.cfg.smile_parameter, new_smile, mode="set"
            ),
            self.plugin.set_parameter_value(
                self.cfg.open_parameter, new_open, mode="set"
            ),
        )
        # 更新当前表情状态
        self._current_smile = new_smile
        self._current_open = new_open

    def get_controlled_parameters(self) -> List[str]:
        """返回嘴部表情控制器控制的参数列表"""
        return [self.cfg.smile_parameter, self.cfg.open_parameter]
