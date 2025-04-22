import asyncio
import random
from .base_animation import BaseAnimation
from .easing import ease_in_out_sine

class BodySwingAnimation(BaseAnimation):
    """身体随机摇摆及眼睛跟随动画"""
    def __init__(self, plugin, config, logger):
        super().__init__(plugin, config, logger)
        # 提取身体摇摆与眼睛跟随的配置
        self.body_cfg = config.body_swing
        self.eye_cfg = config.eye_follow
        self.current_x = 0.0
        self.current_z = 0.0
        self.current_eye_x = 0.0
        self.current_eye_y = 0.0

    async def run(self):
        self.logger.info("启动身体摇摆效果...")
        try:
            while True:
                await self._swing_cycle()
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            self.logger.info("BodySwingAnimation 已取消")
            raise

    async def _swing_cycle(self):
        # 随机生成目标位置
        for _ in range(10):
            target_x = random.uniform(self.body_cfg.X_MIN, self.body_cfg.X_MAX)
            target_z = random.uniform(self.body_cfg.Z_MIN, self.body_cfg.Z_MAX)
            if abs(target_x - self.current_x) > 5.0 or abs(target_z - self.current_z) > 7.5:
                break
        duration = random.uniform(self.body_cfg.MIN_DURATION, self.body_cfg.MAX_DURATION)
        easing = ease_in_out_sine
        start = asyncio.get_event_loop().time()
        end = start + duration
        start_x, start_z = self.current_x, self.current_z

        # 计算眼睛跟随目标
        if self.eye_cfg.ENABLED:
            x_range = self.body_cfg.X_MAX - self.body_cfg.X_MIN
            z_range = self.body_cfg.Z_MAX - self.body_cfg.Z_MIN
            norm_x = (target_x - self.body_cfg.X_MIN) / x_range if x_range != 0 else 0
            norm_z = (target_z - self.body_cfg.Z_MIN) / z_range if z_range != 0 else 0
            target_eye_x = self.eye_cfg.X_MIN_RANGE + norm_x * (self.eye_cfg.X_MAX_RANGE - self.eye_cfg.X_MIN_RANGE)
            target_eye_y = self.eye_cfg.Y_MIN_RANGE + norm_z * (self.eye_cfg.Y_MAX_RANGE - self.eye_cfg.Y_MIN_RANGE)
        else:
            target_eye_x, target_eye_y = self.current_eye_x, self.current_eye_y

        while True:
            now = asyncio.get_event_loop().time()
            if now >= end:
                break
            prog = min(1.0, (now - start) / duration)
            eased = easing(prog)
            x = start_x + (target_x - start_x) * eased
            z = start_z + (target_z - start_z) * eased
            eye_x = self.current_eye_x + (target_eye_x - self.current_eye_x) * eased
            eye_y = self.current_eye_y + (target_eye_y - self.current_eye_y) * eased
            try:
                await self.plugin.set_parameter_value(self.body_cfg.X_PARAMETER, x, mode="set")
                await self.plugin.set_parameter_value(self.body_cfg.Z_PARAMETER, z, mode="set")
                if self.eye_cfg.ENABLED:
                    await self.plugin.set_parameter_value(self.eye_cfg.LEFT_X_PARAMETER, eye_x, mode="set")
                    await self.plugin.set_parameter_value(self.eye_cfg.RIGHT_X_PARAMETER, eye_x, mode="set")
                    await self.plugin.set_parameter_value(self.eye_cfg.LEFT_Y_PARAMETER, eye_y, mode="set")
                    await self.plugin.set_parameter_value(self.eye_cfg.RIGHT_Y_PARAMETER, eye_y, mode="set")
            except Exception as e:
                if isinstance(e, asyncio.CancelledError):
                    raise
                self.logger.error(f"身体摇摆出错: {e}")
                return
            await asyncio.sleep(0.033)

        # 确保到达目标
        await self.plugin.set_parameter_value(self.body_cfg.X_PARAMETER, target_x, mode="set")
        await self.plugin.set_parameter_value(self.body_cfg.Z_PARAMETER, target_z, mode="set")
        if self.eye_cfg.ENABLED:
            await self.plugin.set_parameter_value(self.eye_cfg.LEFT_X_PARAMETER, target_eye_x, mode="set")
            await self.plugin.set_parameter_value(self.eye_cfg.RIGHT_X_PARAMETER, target_eye_x, mode="set")
            await self.plugin.set_parameter_value(self.eye_cfg.LEFT_Y_PARAMETER, target_eye_y, mode="set")
            await self.plugin.set_parameter_value(self.eye_cfg.RIGHT_Y_PARAMETER, target_eye_y, mode="set")
        # 更新当前位置
        self.current_x, self.current_z = target_x, target_z
        self.current_eye_x, self.current_eye_y = target_eye_x, target_eye_y
