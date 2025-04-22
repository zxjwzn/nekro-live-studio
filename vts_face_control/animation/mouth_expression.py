import asyncio
import random
from .base_animation import BaseAnimation
from .easing import ease_in_out_sine

class MouthExpressionAnimation(BaseAnimation):
    """随机嘴部表情动画"""
    def __init__(self, plugin, config, logger):
        super().__init__(plugin, config, logger)
        self.current_smile = 0.0
        self.current_open = 0.0

    async def run(self):
        self.logger.info("启动嘴部表情效果...")
        try:
            while True:
                try:
                    await self._expression_cycle()
                except Exception as e:
                    if isinstance(e, asyncio.CancelledError):
                        self.logger.info("MouthExpressionAnimation 已取消")
                        raise
                    self.logger.error(f"嘴部表情周期出错: {e}")
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            self.logger.info("MouthExpressionAnimation 已取消")
            raise

    async def _expression_cycle(self):
        # 随机生成表情目标
        for _ in range(10):
            new_smile = random.uniform(self.config.SMILE_MIN, self.config.SMILE_MAX)
            if random.random() < 0.7:
                new_open = random.uniform(self.config.OPEN_MIN, self.config.OPEN_MIN + 0.2)
            else:
                new_open = random.uniform(self.config.OPEN_MIN + 0.2, self.config.OPEN_MAX)
            if abs(new_smile - self.current_smile) > 0.1 or abs(new_open - self.current_open) > 0.1:
                break

        duration = random.uniform(self.config.CHANGE_MIN_DURATION, self.config.CHANGE_MAX_DURATION)
        start_smile = self.current_smile
        start_open = self.current_open
        start = asyncio.get_event_loop().time()
        end = start + duration

        while True:
            now = asyncio.get_event_loop().time()
            if now >= end:
                break
            t = min(1.0, (now - start) / duration)
            eased = ease_in_out_sine(t)
            smile_val = start_smile + (new_smile - start_smile) * eased
            open_val = start_open + (new_open - start_open) * eased
            try:
                await self.plugin.set_parameter_value(self.config.SMILE_PARAMETER, smile_val, mode="set")
                await self.plugin.set_parameter_value(self.config.OPEN_PARAMETER, open_val, mode="set")
            except Exception as e:
                if isinstance(e, asyncio.CancelledError):
                    raise
                self.logger.error(f"嘴部表情变化出错: {e}")
                return
            await asyncio.sleep(0.033)

        # 设置最终表情
        try:
            await self.plugin.set_parameter_value(self.config.SMILE_PARAMETER, new_smile, mode="set")
            await self.plugin.set_parameter_value(self.config.OPEN_PARAMETER, new_open, mode="set")
        except Exception as e:
            if isinstance(e, asyncio.CancelledError):
                raise
            self.logger.error(f"设置嘴部表情结束值出错: {e}")

        self.current_smile = new_smile
        self.current_open = new_open
