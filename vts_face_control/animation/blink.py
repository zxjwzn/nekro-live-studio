import asyncio
import random
from .base_animation import BaseAnimation
from .easing import ease_in_sine

class BlinkAnimation(BaseAnimation):
    """自动眨眼动画"""
    async def run(self):
        self.logger.info("启动自动眨眼效果...")
        try:
            while True:
                wait_time = random.uniform(self.config.MIN_INTERVAL, self.config.MAX_INTERVAL)
                self.logger.debug(f"下次眨眼等待: {wait_time:.2f} 秒")
                try:
                    await asyncio.wait_for(asyncio.sleep(wait_time), timeout=wait_time + 1)
                except asyncio.TimeoutError:
                    pass
                await self._blink_cycle()
        except asyncio.CancelledError:
            self.logger.info("BlinkAnimation 已取消")
            raise

    async def _blink_cycle(self):
        # 闭眼阶段
        start = asyncio.get_event_loop().time()
        end = start + self.config.CLOSE_DURATION
        while True:
            now = asyncio.get_event_loop().time()
            if now >= end:
                break
            progress = min(1.0, (now - start) / self.config.CLOSE_DURATION)
            # 值从 MAX_VALUE 降到 MIN_VALUE
            value = self.config.MAX_VALUE * (1.0 - ease_in_sine(progress))
            try:
                await self.plugin.set_parameter_value(self.config.LEFT_PARAMETER, value, mode="set")
                await self.plugin.set_parameter_value(self.config.RIGHT_PARAMETER, value, mode="set")
            except Exception as e:
                if isinstance(e, asyncio.CancelledError):
                    raise
                self.logger.error(f"眨眼闭合阶段出错: {e}")
                return
            await asyncio.sleep(0.016)
        # 保持闭眼
        try:
            await self.plugin.set_parameter_value(self.config.LEFT_PARAMETER, self.config.MIN_VALUE, mode="set")
            await self.plugin.set_parameter_value(self.config.RIGHT_PARAMETER, self.config.MIN_VALUE, mode="set")
        except Exception as e:
            if isinstance(e, asyncio.CancelledError):
                raise
            self.logger.error(f"保持闭眼时出错: {e}")
        await asyncio.sleep(self.config.CLOSED_HOLD)
        # 睁眼阶段
        start = asyncio.get_event_loop().time()
        end = start + self.config.OPEN_DURATION
        while True:
            now = asyncio.get_event_loop().time()
            if now >= end:
                break
            progress = min(1.0, (now - start) / self.config.OPEN_DURATION)
            # 值从 MIN_VALUE 升到 MAX_VALUE
            value = self.config.MAX_VALUE * ease_in_sine(progress)
            try:
                await self.plugin.set_parameter_value(self.config.LEFT_PARAMETER, value, mode="set")
                await self.plugin.set_parameter_value(self.config.RIGHT_PARAMETER, value, mode="set")
            except Exception as e:
                if isinstance(e, asyncio.CancelledError):
                    raise
                self.logger.error(f"眨眼睁眼阶段出错: {e}")
                return
            await asyncio.sleep(0.016)
        # 确保睁眼
        try:
            await self.plugin.set_parameter_value(self.config.LEFT_PARAMETER, self.config.MAX_VALUE, mode="set")
            await self.plugin.set_parameter_value(self.config.RIGHT_PARAMETER, self.config.MAX_VALUE, mode="set")
        except Exception as e:
            if isinstance(e, asyncio.CancelledError):
                raise
            self.logger.error(f"完成眨眼阶段出错: {e}")
