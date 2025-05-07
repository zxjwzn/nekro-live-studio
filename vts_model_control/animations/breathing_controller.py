import asyncio
from configs.config import config
from utils.tweener import Tweener
from utils.easing import Easing
from .base_controller import BaseController
from typing import List
import random

class BreathingController(BaseController):
    """呼吸控制器，使用 Tweener 实现吸气-呼气循环"""
    def __init__(self):
        super().__init__()
        self.cfg = config.breathing
        self.skip_pause = True
    async def run_cycle(self):
        """执行一次呼吸（吸气-呼气）循环"""
        # 随机微扰：值幅度 ±5%，时长 ±10%
        jitter_val = 0.05
        jitter_dur = 0.1
        total_range = self.cfg.max_value - self.cfg.min_value
        delta_val = total_range * jitter_val
        v_min = self.cfg.min_value + random.uniform(-delta_val, delta_val)
        v_max = self.cfg.max_value + random.uniform(-delta_val, delta_val)
        inhale_dur = self.cfg.inhale_duration + random.uniform(-self.cfg.inhale_duration * jitter_dur, self.cfg.inhale_duration * jitter_dur)
        exhale_dur = self.cfg.exhale_duration + random.uniform(-self.cfg.exhale_duration * jitter_dur, self.cfg.exhale_duration * jitter_dur)

        # 吸气阶段（随机时长&幅度）
        await Tweener.tween(
            self.plugin,
            self.cfg.parameter,
            v_min,
            v_max,
            inhale_dur,
            Easing.out_sine
        )
        # 确保最终状态
        await self.plugin.set_parameter_value(self.cfg.parameter, v_max, mode="set")

        # 呼气阶段（随机时长&幅度）
        await Tweener.tween(
            self.plugin,
            self.cfg.parameter,
            v_max,
            v_min,
            exhale_dur,
            Easing.out_sine
        )
        # 确保最终状态
        await self.plugin.set_parameter_value(self.cfg.parameter, v_min, mode="set")

    def get_controlled_parameters(self) -> List[str]:
        """返回呼吸控制器控制的参数列表"""
        return [self.cfg.parameter]
