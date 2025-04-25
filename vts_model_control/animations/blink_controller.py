import asyncio
import random
from configs.config import config
from utils.tweener import Tweener
from utils.easing import Easing
from utils.logger import logger
from services.plugin import plugin
from .base_controller import BaseController
from typing import List

class BlinkController(BaseController):
    """眨眼控制器，使用 Tweener 实现闭眼-睁眼过渡循环"""
    def __init__(self):
        super().__init__()
        self.cfg = config.blink
        self.skip_pause = False
    async def run_cycle(self):
        """执行一次眨眼周期: 闭眼-保持-睁眼-等待"""
        logger.info("开始眨眼周期")
        # 闭眼
        logger.info(f"开始闭眼 (缓动 {self.cfg.max_value:.2f} -> {self.cfg.min_value:.2f})")
        await asyncio.gather(
            Tweener.tween(
                self.plugin,
                self.cfg.left_parameter,
                self.cfg.max_value,
                self.cfg.min_value,
                self.cfg.close_duration,
                Easing.out_sine
            ),
            Tweener.tween(
                self.plugin,
                self.cfg.right_parameter,
                self.cfg.max_value,
                self.cfg.min_value,
                self.cfg.close_duration,
                Easing.out_sine
            ),
        )
        # 保持闭眼
        logger.info(f"保持闭眼 {self.cfg.closed_hold:.2f} 秒")
        await asyncio.sleep(self.cfg.closed_hold)
        # 睁眼
        logger.info(f"开始睁眼 (缓动 {self.cfg.min_value:.2f} -> {self.cfg.max_value:.2f})")
        await asyncio.gather(
            Tweener.tween(
                self.plugin,
                self.cfg.left_parameter,
                self.cfg.min_value,
                self.cfg.max_value,
                self.cfg.open_duration,
                Easing.in_sine
            ),
            Tweener.tween(
                self.plugin,
                self.cfg.right_parameter,
                self.cfg.min_value,
                self.cfg.max_value,
                self.cfg.open_duration,
                Easing.in_sine
            ),
        )
        # 确保最终睁眼
        await asyncio.gather(
            self.plugin.set_parameter_value(self.cfg.left_parameter, self.cfg.max_value, mode="set"),
            self.plugin.set_parameter_value(self.cfg.right_parameter, self.cfg.max_value, mode="set")
        )
        logger.info("眨眼动画完成，确保眼睛保持睁开")
        # 随机等待下一次眨眼
        wait_time = random.uniform(self.cfg.min_interval, self.cfg.max_interval)
        logger.info(f"下次眨眼等待: {wait_time:.2f} 秒")
        try:
            await asyncio.wait_for(asyncio.sleep(wait_time), timeout=wait_time + 1)
        except asyncio.TimeoutError:
            pass
    def get_controlled_parameters(self) -> List[str]:
        """返回眨眼控制器控制的参数列表"""
        return [self.cfg.left_parameter, self.cfg.right_parameter]