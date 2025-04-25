import asyncio
import random
from configs.config import config
from utils.tweener import Tweener
from utils.easing import Easing
from utils.logger import logger
from .base_controller import BaseController
from typing import List

class BodySwingController(BaseController):
    """身体摇摆控制器，使用 Tweener 实现随机摆动并同步眼睛跟随"""
    def __init__(self):
        super().__init__()
        self.cfg = config.body_swing
        self.eye_cfg = config.eye_follow
        self._current_x = 0.0
        self._current_z = 0.0
        self._eye_x = 0.0
        self._eye_y = 0.0
        self.skip_pause = True
    async def run_cycle(self):
        """执行一次身体摇摆及眼睛跟随周期"""
        # 随机生成目标值
        new_x = random.uniform(self.cfg.x_min, self.cfg.x_max)
        new_z = random.uniform(self.cfg.z_min, self.cfg.z_max)
        duration = random.uniform(self.cfg.min_duration, self.cfg.max_duration)
        eye_x = eye_y = 0.0
        # 计算眼睛目标值
        if self.eye_cfg.enabled:
            x_range = self.cfg.x_max - self.cfg.x_min
            x_norm = (new_x - self.cfg.x_min) / x_range if x_range else 0
            eye_x = self.eye_cfg.x_min_range + x_norm * (self.eye_cfg.x_max_range - self.eye_cfg.x_min_range)
            z_range = self.cfg.z_max - self.cfg.z_min
            z_norm = (new_z - self.cfg.z_min) / z_range if z_range else 0
            eye_y = self.eye_cfg.y_min_range + z_norm * (self.eye_cfg.y_max_range - self.eye_cfg.y_min_range)
        easing_func = Tweener.random_easing()
        # 执行动画
        tasks = [
            Tweener.tween(self.plugin, self.cfg.x_parameter, self._current_x, new_x, duration, easing_func),
            Tweener.tween(self.plugin, self.cfg.z_parameter, self._current_z, new_z, duration, easing_func)
        ]
        logger.info(
            f"随机摇摆参数: 当前位置=({self._current_x:.2f}, {self._current_z:.2f}), 目标=({new_x:.2f}, {new_z:.2f}), "
            f"持续时间={duration:.2f}s, 缓动函数={easing_func.__name__}"
        )
        if self.eye_cfg.enabled:
            logger.info(
                f"眼睛跟随: 当前=({self._eye_x:.2f}, {self._eye_y:.2f}), 目标=({eye_x:.2f}, {eye_y:.2f})"
            )
            tasks.extend([
                Tweener.tween(self.plugin, self.eye_cfg.left_x_parameter, self._eye_x, eye_x, duration, easing_func),
                Tweener.tween(self.plugin, self.eye_cfg.right_x_parameter, self._eye_x, eye_x, duration, easing_func),
                Tweener.tween(self.plugin, self.eye_cfg.left_y_parameter, self._eye_y, eye_y, duration, easing_func),
                Tweener.tween(self.plugin, self.eye_cfg.right_y_parameter, self._eye_y, eye_y, duration, easing_func)
            ])
        await asyncio.gather(*tasks)
        # 确保最终位置
        final_tasks = [
            self.plugin.set_parameter_value(self.cfg.x_parameter, new_x, mode="set"),
            self.plugin.set_parameter_value(self.cfg.z_parameter, new_z, mode="set")
        ]
        if self.eye_cfg.enabled:
            final_tasks.extend([
                self.plugin.set_parameter_value(self.eye_cfg.left_x_parameter, eye_x, mode="set"),
                self.plugin.set_parameter_value(self.eye_cfg.right_x_parameter, eye_x, mode="set"),
                self.plugin.set_parameter_value(self.eye_cfg.left_y_parameter, eye_y, mode="set"),
                self.plugin.set_parameter_value(self.eye_cfg.right_y_parameter, eye_y, mode="set")
            ])
        await asyncio.gather(*final_tasks)
        # 更新当前值
        self._current_x, self._current_z = new_x, new_z
        if self.eye_cfg.enabled:
            self._eye_x, self._eye_y = eye_x, eye_y
    def get_controlled_parameters(self) -> List[str]:
        """返回身体摇摆控制器控制的参数列表"""
        params = [self.cfg.x_parameter, self.cfg.z_parameter]
        params += [
            self.eye_cfg.left_x_parameter,
            self.eye_cfg.right_x_parameter,
            self.eye_cfg.left_y_parameter,
            self.eye_cfg.right_y_parameter
        ]
        return params 