import asyncio
import random
from configs.config import config
from animation.tweener import Tweener
from animation.easing import Easing
from utils.logger import logger
class BodySwingController:
    """身体摇摆控制器，使用 Tweener 实现随机摆动并同步眼睛跟随"""
    def __init__(self, plugin):
        self.plugin = plugin
        self.cfg = config.body_swing
        self.eye_cfg = config.eye_follow
        self._stop_event = asyncio.Event()
        self._task = None
        self._current_x = 0.0
        self._current_z = 0.0
        self._eye_x = 0.0
        self._eye_y = 0.0

    async def start(self):
        """启动身体摆动循环"""
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self):
        """停止身体摆动循环"""
        self._stop_event.set()
        if self._task:
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self):
        while not self._stop_event.is_set():
            if self._stop_event.is_set():
                break
            # 随机生成目标值
            new_x = random.uniform(self.cfg.X_MIN, self.cfg.X_MAX)
            new_z = random.uniform(self.cfg.Z_MIN, self.cfg.Z_MAX)
            duration = random.uniform(self.cfg.MIN_DURATION, self.cfg.MAX_DURATION)
            eye_x = 0.0
            eye_y = 0.0
            # 计算眼睛目标值
            if self.eye_cfg.ENABLED:
                x_norm = (new_x - self.cfg.X_MIN) / (self.cfg.X_MAX - self.cfg.X_MIN) if (self.cfg.X_MAX - self.cfg.X_MIN) != 0 else 0
                eye_x = self.eye_cfg.X_MIN_RANGE + x_norm * (self.eye_cfg.X_MAX_RANGE - self.eye_cfg.X_MIN_RANGE)
                z_norm = (new_z - self.cfg.Z_MIN) / (self.cfg.Z_MAX - self.cfg.Z_MIN) if (self.cfg.Z_MAX - self.cfg.Z_MIN) != 0 else 0
                eye_y = self.eye_cfg.Y_MIN_RANGE + z_norm * (self.eye_cfg.Y_MAX_RANGE - self.eye_cfg.Y_MIN_RANGE)
            easing_func = Tweener.random_easing()
            # 并行动画
            tasks = [
                Tweener.tween(self.plugin, self.cfg.X_PARAMETER, self._current_x, new_x, duration, easing_func),
                Tweener.tween(self.plugin, self.cfg.Z_PARAMETER, self._current_z, new_z, duration, easing_func)
            ]
            logger.info(f"随机摇摆参数: 当前位置=({self._current_x:.2f}, {self._current_z:.2f}), "
                    f"目标=({new_x:.2f}, {new_z:.2f}), "
                    f"持续时间={duration:.2f}s, 缓动函数={easing_func.__name__}")
            if self.eye_cfg.ENABLED:
                logger.info(f"眼睛跟随: 当前=({self._eye_x:.2f}, {self._eye_y:.2f}), "
                    f"目标=({eye_x:.2f}, {eye_y:.2f})")
                tasks.extend([
                    Tweener.tween(self.plugin, self.eye_cfg.LEFT_X_PARAMETER, self._eye_x, eye_x, duration, easing_func),
                    Tweener.tween(self.plugin, self.eye_cfg.RIGHT_X_PARAMETER, self._eye_x, eye_x, duration, easing_func),
                    Tweener.tween(self.plugin, self.eye_cfg.LEFT_Y_PARAMETER, self._eye_y, eye_y, duration, easing_func),
                    Tweener.tween(self.plugin, self.eye_cfg.RIGHT_Y_PARAMETER, self._eye_y, eye_y, duration, easing_func)
                ])
            await asyncio.gather(*tasks)

            #确保最终位置
            final_task = [
                self.plugin.set_parameter_value(self.cfg.X_PARAMETER, new_x, mode="set"),
                self.plugin.set_parameter_value(self.cfg.Z_PARAMETER, new_z, mode="set")
            ]
            if self.eye_cfg.ENABLED:
                final_task.extend([
                    self.plugin.set_parameter_value(self.eye_cfg.LEFT_X_PARAMETER, eye_x, mode="set"),
                    self.plugin.set_parameter_value(self.eye_cfg.RIGHT_X_PARAMETER, eye_x, mode="set"),
                    self.plugin.set_parameter_value(self.eye_cfg.LEFT_Y_PARAMETER, eye_y, mode="set"),
                    self.plugin.set_parameter_value(self.eye_cfg.RIGHT_Y_PARAMETER, eye_y, mode="set")
                ])
            await asyncio.gather(*final_task)

            # 更新当前值
            self._current_x = new_x
            self._current_z = new_z
            if self.eye_cfg.ENABLED:
                self._eye_x = eye_x
                self._eye_y = eye_y 