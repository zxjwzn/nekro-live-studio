import asyncio
import random
from configs.config import config
from services.tweener import Tweener
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
        self._current_eye_left = 0.0
        self._current_eye_right = 0.0
    async def run_cycle(self):
        """执行一次眨眼周期: 在 tween/closed_hold/open 阶段完成眨眼，等待阶段可被取消"""
        logger.info("开始眨眼周期")
        cancelled = False
        try:
            # 闭眼
            logger.info(f"开始闭眼 (缓动 {self._current_eye_left:.2f} -> {self.cfg.min_value:.2f})")
            await asyncio.gather(
                Tweener.tween(
                    self.plugin,
                    self.cfg.left_parameter,
                    self._current_eye_left,
                    self.cfg.min_value,
                    self.cfg.close_duration,
                    Easing.out_sine
                ),
                Tweener.tween(
                    self.plugin,
                    self.cfg.right_parameter,
                    self._current_eye_right,
                    self.cfg.min_value,
                    self.cfg.close_duration,
                    Easing.out_sine
                ),
            )
            self._current_eye_left = self.cfg.min_value
            self._current_eye_right = self.cfg.min_value
            # 保持闭眼
            logger.info(f"保持闭眼 {self.cfg.closed_hold:.2f} 秒")
            await asyncio.sleep(self.cfg.closed_hold)
            # 睁眼
            logger.info(f"开始睁眼 (缓动 {self._current_eye_left:.2f} -> {self.cfg.max_value:.2f})")
            await asyncio.gather(
                Tweener.tween(
                    self.plugin,
                    self.cfg.left_parameter,
                    self._current_eye_left,
                    self.cfg.max_value,
                    self.cfg.open_duration,
                    Easing.in_sine
                ),
                Tweener.tween(
                    self.plugin,
                    self.cfg.right_parameter,
                    self._current_eye_right,
                    self.cfg.max_value,
                    self.cfg.open_duration,
                    Easing.in_sine
                ),
            )
            self._current_eye_left = self.cfg.max_value
            self._current_eye_right = self.cfg.max_value
        except asyncio.CancelledError:
            # 收到取消信号，仍要完成关键闭眼->睁眼动作
            cancelled = True
        # 确保最终睁眼
        await asyncio.gather(
            self.plugin.set_parameter_value(self.cfg.left_parameter, self._current_eye_left, mode="set"),
            self.plugin.set_parameter_value(self.cfg.right_parameter, self._current_eye_right, mode="set")
        )
        logger.info("眨眼动画完成，确保眼睛保持睁开")
        # 如果在 tween 阶段收到取消，或外部 stop 事件，退出本周期
        if cancelled or self._stop_event.is_set():
            return
        # 随机等待下一次眨眼，睡眠阶段可被取消立即退出
        wait_time = random.uniform(self.cfg.min_interval, self.cfg.max_interval)
        logger.info(f"下次眨眼等待: {wait_time:.2f} 秒")
        try:
            await asyncio.sleep(wait_time)
        except asyncio.CancelledError:
            # 在等待阶段取消，则退出
            return
    def get_controlled_parameters(self) -> List[str]:
        """返回眨眼控制器控制的参数列表"""
        return [self.cfg.left_parameter, self.cfg.right_parameter]