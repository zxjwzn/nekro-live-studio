import asyncio
import random
from typing import List

from configs.config import config
from services.vts_plugin import plugin
from utils.easing import Easing
from utils.logger import logger
from services.tweener import tweener

from .base_controller import BaseController


class BodySwingController(BaseController):
    """身体摇摆控制器, 通过缓动 FaceAngleX/Z 实现更自然的待机动作。"""

    def __init__(self):
        super().__init__()
        self.cfg = config.BODY_SWING
        self.eye_cfg = config.EYE_FOLLOW
        self._current_x = tweener.controlled_params.get(self.cfg.X_PARAMETER, 0.0)
        self._current_z = tweener.controlled_params.get(self.cfg.Z_PARAMETER, 0.0)
        self._eye_x = 0.0
        self._eye_y = 0.0

    async def run_cycle(self):
        """执行一次身体摇摆周期。"""
        target_x = random.uniform(self.cfg.X_MIN, self.cfg.X_MAX)
        target_z = random.uniform(self.cfg.Z_MIN, self.cfg.Z_MAX)
        duration = random.uniform(self.cfg.MIN_DURATION, self.cfg.MAX_DURATION)
        eye_x = eye_y = 0.0
        x_range = self.cfg.X_MAX - self.cfg.X_MIN
        x_norm = (target_x - self.cfg.X_MIN) / x_range if x_range else 0
        eye_x = self.eye_cfg.X_MIN_RANGE + x_norm * (self.eye_cfg.X_MAX_RANGE - self.eye_cfg.X_MIN_RANGE)
        z_range = self.cfg.Z_MAX - self.cfg.Z_MIN
        z_norm = (target_z - self.cfg.Z_MIN) / z_range if z_range else 0
        # 反向映射 z_norm 到垂直方向：使眼睛看向屏幕中心，z 越大时 eye_y 越小
        eye_y = self.eye_cfg.Y_MAX_RANGE - z_norm * (self.eye_cfg.Y_MAX_RANGE - self.eye_cfg.Y_MIN_RANGE)
        easing_func = tweener.random_easing()

        try:
            logger.info(
                f"身体摇摆: "
                f"X: {self._current_x:.2f} -> {target_x:.2f}, "
                f"Z: {self._current_z:.2f} -> {target_z:.2f}, "
                f"时长: {duration:.2f}s, 缓动: {easing_func.__name__}"
            )
            logger.info(f"眼睛跟随: 当前=({self._eye_x:.2f}, {self._eye_y:.2f}), 目标=({eye_x:.2f}, {eye_y:.2f})")
            await asyncio.gather(
                tweener.tween(self.cfg.X_PARAMETER, self._current_x, target_x, duration, easing_func),
                tweener.tween(self.cfg.Z_PARAMETER, self._current_z, target_z, duration, easing_func),
                tweener.tween(self.eye_cfg.LEFT_X_PARAMETER, self._eye_x, eye_x, duration, easing_func),
                tweener.tween(self.eye_cfg.RIGHT_X_PARAMETER, self._eye_x, eye_x, duration, easing_func),
                tweener.tween(self.eye_cfg.LEFT_Y_PARAMETER, self._eye_y, eye_y, duration, easing_func),
                tweener.tween(self.eye_cfg.RIGHT_Y_PARAMETER, self._eye_y, eye_y, duration, easing_func),
            )
            self._current_x = target_x
            self._current_z = target_z

            self._eye_x, self._eye_y = eye_x, eye_y
        except asyncio.CancelledError:
            raise
