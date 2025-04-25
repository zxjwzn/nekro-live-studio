import asyncio
from configs.config import config
from utils.tweener import Tweener
from utils.easing import Easing
from .base_controller import BaseController
from typing import List

class BreathingController(BaseController):
    """呼吸控制器，使用 Tweener 实现吸气-呼气循环"""
    def __init__(self):
        super().__init__()
        self.cfg = config.breathing
        self.skip_pause = True
    async def run_cycle(self):
        """执行一次呼吸（吸气-呼气）循环"""
        # 吸气阶段
        #easing_func = Tweener.random_easing()
        await Tweener.tween(
            self.plugin,
            self.cfg.parameter,
            self.cfg.min_value,
            self.cfg.max_value,
            self.cfg.inhale_duration,
            Easing.out_sine
        )
        # 确保最终状态
        await self.plugin.set_parameter_value(self.cfg.parameter, self.cfg.max_value, mode="set")

        # 呼气阶段
        await Tweener.tween(
            self.plugin,
            self.cfg.parameter,
            self.cfg.max_value,
            self.cfg.min_value,
            self.cfg.exhale_duration,
            Easing.out_sine
        )
        # 确保最终状态
        await self.plugin.set_parameter_value(self.cfg.parameter, self.cfg.min_value, mode="set")

    def get_controlled_parameters(self) -> List[str]:
        """返回呼吸控制器控制的参数列表"""
        return [self.cfg.parameter]
