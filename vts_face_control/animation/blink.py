import asyncio
import random
from .base_animation import BaseAnimation
from .easing import ease_in_sine

class BlinkAnimation(BaseAnimation):
    """自动眨眼动画"""
    async def run(self, shutdown_event: asyncio.Event):
        self.logger.info("启动自动眨眼效果...")
        try:
            while not shutdown_event.is_set():
                # 随机等待一段时间
                wait_time = random.uniform(self.config.MIN_INTERVAL, self.config.MAX_INTERVAL)
                self.logger.debug(f"下次眨眼等待: {wait_time:.2f} 秒")
                try:
                    # 使用 asyncio.wait_for 来允许在等待期间被中断
                    await asyncio.wait_for(asyncio.sleep(wait_time), timeout=wait_time + 1)
                except asyncio.TimeoutError:
                    pass # 正常等待完成
                
                if shutdown_event.is_set():
                    break # 检查是否在等待期间收到了关闭信号
                
                # 执行眨眼
                self.logger.debug("执行眨眼...")
                try:
                    success = await self._blink_cycle()
                    if not success:
                        # 如果眨眼周期执行失败，暂停一下再继续
                        await asyncio.sleep(1.0)
                except Exception as e:
                    if isinstance(e, asyncio.CancelledError):
                        raise
                    self.logger.error(f"眨眼周期出错: {e}")
        except asyncio.CancelledError:
            self.logger.info("BlinkAnimation 已取消")
            raise

    async def _blink_cycle(self):
        """执行一次完整的眨眼周期，返回是否成功"""
        try:
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
                    return False
                await asyncio.sleep(0.016)
                
            # 保持闭眼
            try:
                await self.plugin.set_parameter_value(self.config.LEFT_PARAMETER, self.config.MIN_VALUE, mode="set")
                await self.plugin.set_parameter_value(self.config.RIGHT_PARAMETER, self.config.MIN_VALUE, mode="set")
            except Exception as e:
                if isinstance(e, asyncio.CancelledError):
                    raise
                self.logger.error(f"保持闭眼时出错: {e}")
                return False
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
                    return False
                await asyncio.sleep(0.016)
                
            # 确保睁眼
            try:
                await self.plugin.set_parameter_value(self.config.LEFT_PARAMETER, self.config.MAX_VALUE, mode="set")
                await self.plugin.set_parameter_value(self.config.RIGHT_PARAMETER, self.config.MAX_VALUE, mode="set")
            except Exception as e:
                if isinstance(e, asyncio.CancelledError):
                    raise
                self.logger.error(f"完成眨眼阶段出错: {e}")
                return False
                
            return True
        except Exception as e:
            if isinstance(e, asyncio.CancelledError):
                raise
            self.logger.error(f"执行眨眼周期发生意外错误: {e}")
            return False
