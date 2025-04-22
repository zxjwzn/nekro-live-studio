import asyncio
from .base_animation import BaseAnimation
from .easing import ease_in_out_sine

class BreathingAnimation(BaseAnimation):
    """呼吸动画"""
    async def run(self):
        self.logger.info("启动呼吸效果...")
        try:
            while True:
                try:
                    await self._breathe_cycle()
                except Exception as e:
                    if isinstance(e, asyncio.CancelledError):
                        self.logger.info("BreathingAnimation 已取消")
                        raise
                    self.logger.error(f"呼吸周期出错: {e}")
                await asyncio.sleep(0)
        except asyncio.CancelledError:
            self.logger.info("BreathingAnimation run 已取消")
            raise

    async def _breathe_cycle(self):
        # 吸气阶段
        start = asyncio.get_event_loop().time()
        end = start + self.config.INHALE_DURATION
        while True:
            now = asyncio.get_event_loop().time()
            if now >= end:
                break
            prog = min(1.0, (now - start) / self.config.INHALE_DURATION)
            val = self.config.MIN_VALUE + (self.config.MAX_VALUE - self.config.MIN_VALUE) * ease_in_out_sine(prog)
            try:
                await self.plugin.set_parameter_value(self.config.PARAMETER, val, mode="add")
            except Exception as e:
                if isinstance(e, asyncio.CancelledError):
                    raise
                self.logger.error(f"呼吸吸气阶段出错: {e}")
                return
            await asyncio.sleep(0.016)
        # 呼气阶段
        start = asyncio.get_event_loop().time()
        end = start + self.config.EXHALE_DURATION
        while True:
            now = asyncio.get_event_loop().time()
            if now >= end:
                break
            prog = min(1.0, (now - start) / self.config.EXHALE_DURATION)
            val = self.config.MAX_VALUE - (self.config.MAX_VALUE - self.config.MIN_VALUE) * ease_in_out_sine(prog)
            try:
                await self.plugin.set_parameter_value(self.config.PARAMETER, val, mode="add")
            except Exception as e:
                if isinstance(e, asyncio.CancelledError):
                    raise
                self.logger.error(f"呼吸呼气阶段出错: {e}")
                return
            await asyncio.sleep(0.016)
