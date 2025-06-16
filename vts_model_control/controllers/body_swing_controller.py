import asyncio
import random
from pathlib import Path
from typing import Type

from pydantic import Field
from services.tweener import tweener
from utils.logger import logger

from configs.base import ConfigBase

from .base_controller import CONFIG_DIR, IdleController


class BodySwingConfig(ConfigBase):
    """身体摇摆配置"""

    ENABLED: bool = Field(default=True, description="是否启用身体摇摆效果")
    X_MIN: float = Field(default=-10.0, description="身体左右摇摆最小位置（左侧）")
    X_MAX: float = Field(default=15.0, description="身体左右摇摆最大位置（右侧）")
    Z_MIN: float = Field(default=-10.0, description="上肢旋转最小位置（下方）")
    Z_MAX: float = Field(default=15.0, description="上肢旋转最大位置（上方）")
    MIN_DURATION: float = Field(default=2.0, description="摇摆最短持续时间（秒）")
    MAX_DURATION: float = Field(default=8.0, description="摇摆最长持续时间（秒）")
    X_PARAMETER: str = Field(
        default="FaceAngleX",
        description="身体左右摇摆控制的参数名",
    )
    Z_PARAMETER: str = Field(default="FaceAngleZ", description="上肢旋转控制的参数名")


class EyeFollowConfig(ConfigBase):
    """眼睛跟随配置"""

    ENABLED: bool = Field(default=True, description="是否启用眼睛跟随身体摇摆")
    X_MIN_RANGE: float = Field(default=-1.0, description="眼睛左右移动最小值（左侧）")
    X_MAX_RANGE: float = Field(default=1.0, description="眼睛左右移动最大值（右侧）")
    Y_MIN_RANGE: float = Field(default=-1.0, description="眼睛上下移动最小值（下方）")
    Y_MAX_RANGE: float = Field(default=1.0, description="眼睛上下移动最大值（上方）")
    LEFT_X_PARAMETER: str = Field(default="EyeLeftX", description="左眼水平移动参数")
    RIGHT_X_PARAMETER: str = Field(default="EyeRightX", description="右眼水平移动参数")
    LEFT_Y_PARAMETER: str = Field(default="EyeLeftY", description="左眼垂直移动参数")
    RIGHT_Y_PARAMETER: str = Field(default="EyeRightY", description="右眼垂直移动参数")


class BodySwingController(IdleController[BodySwingConfig]):
    """身体摇摆控制器, 通过缓动 FaceAngleX/Z 实现更自然的待机动作。"""

    @classmethod
    def get_config_class(cls) -> Type[BodySwingConfig]:
        return BodySwingConfig

    @classmethod
    def get_config_filename(cls) -> str:
        return "body_swing.yaml"

    def __init__(self):
        super().__init__()
        self.eye_config_path = CONFIG_DIR / "eye_follow.yaml"
        self.eye_config = EyeFollowConfig.load_config(self.eye_config_path)
        self.eye_config.dump_config(self.eye_config_path)

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

        logger.info(f"身体摇摆: X: {target_x:.2f}, Z: {target_z:.2f}, 时长: {duration:.2f}s, 缓动: {easing_func.__name__}")
        if self.eye_config.ENABLED:
            logger.info(f"眼睛跟随: 目标=({eye_x:.2f}, {eye_y:.2f})")
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
