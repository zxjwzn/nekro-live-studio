import asyncio
import random
from typing import Type

from pydantic import Field

from ...services.tweener import tweener
from ...utils.logger import logger
from ..base_controller import IdleController
from ..config import BodySwingConfig, EyeFollowConfig
from ..config_manager import config_manager


class BodySwingController(IdleController[BodySwingConfig]):
    """身体摇摆控制器, 通过缓动 FaceAngleX/Z 实现更自然的待机动作。"""

    @property
    def config(self) -> BodySwingConfig:
        return config_manager.config.body_swing

    @property
    def eye_config(self) -> EyeFollowConfig:
        return config_manager.config.eye_follow

    async def run_cycle(self):
        """执行一次身体摇摆周期。"""
        target_x = random.uniform(self.config.X_MIN, self.config.X_MAX)
        target_z = random.uniform(self.config.Z_MIN, self.config.Z_MAX)
        duration = random.uniform(self.config.MIN_DURATION, self.config.MAX_DURATION)
        eye_x = eye_y = 0.0
        x_range = self.config.X_MAX - self.config.X_MIN
        x_norm = (target_x - self.config.X_MIN) / x_range if x_range else 0
        eye_x = self.eye_config.X_MIN_RANGE + x_norm * (self.eye_config.X_MAX_RANGE - self.eye_config.X_MIN_RANGE)
        z_range = self.config.Z_MAX - self.config.Z_MIN
        z_norm = (target_z - self.config.Z_MIN) / z_range if z_range else 0
        # 反向映射 z_norm 到垂直方向：使眼睛看向屏幕中心，z 越大时 eye_y 越小
        eye_y = self.eye_config.Y_MAX_RANGE - z_norm * (self.eye_config.Y_MAX_RANGE - self.eye_config.Y_MIN_RANGE)
        easing_func = tweener.random_easing()

        logger.debug(f"身体摇摆: X: {target_x:.2f}, Z: {target_z:.2f}, 时长: {duration:.2f}s, 缓动: {easing_func.__name__}")
        if self.eye_config.ENABLED:
            logger.debug(f"眼睛跟随: 目标=({eye_x:.2f}, {eye_y:.2f})")
            await asyncio.gather(
                tweener.tween(
                    param=self.config.X_PARAMETER,
                    end=target_x,
                    duration=duration,
                    easing_func=easing_func,
                ),
                tweener.tween(
                    param=self.config.Z_PARAMETER,
                    end=target_z,
                    duration=duration,
                    easing_func=easing_func,
                ),
                tweener.tween(
                    param=self.eye_config.LEFT_X_PARAMETER,
                    end=eye_x,
                    duration=duration,
                    easing_func=easing_func,
                ),
                tweener.tween(
                    param=self.eye_config.RIGHT_X_PARAMETER,
                    end=eye_x,
                    duration=duration,
                    easing_func=easing_func,
                ),
                tweener.tween(
                    param=self.eye_config.LEFT_Y_PARAMETER,
                    end=eye_y,
                    duration=duration,
                    easing_func=easing_func,
                ),
                tweener.tween(
                    param=self.eye_config.RIGHT_Y_PARAMETER,
                    end=eye_y,
                    duration=duration,
                    easing_func=easing_func,
                ),
            )
        else:
            await asyncio.gather(
                tweener.tween(
                    param=self.config.X_PARAMETER,
                    end=target_x,
                    duration=duration,
                    easing_func=easing_func,
                ),
                tweener.tween(
                    param=self.config.Z_PARAMETER,
                    end=target_z,
                    duration=duration,
                    easing_func=easing_func,
                ),
            )
