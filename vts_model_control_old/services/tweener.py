import asyncio
import random

from utils.easing import Easing


class Tweener:
    """通用的缓动工具类，用于在指定时间内平滑地更新参数值。"""

    @staticmethod
    async def tween(
        plugin,
        param: str,
        start: float,
        end: float,
        duration: float,
        easing_func,
        mode: str = "set",
        fps: int = 60,
    ):
        """优化后的缓动函数：基于步数循环执行插值，根据实际插件调用耗时动态调整帧间睡眠，尽量在 duration 时间内完成。"""
        loop = asyncio.get_event_loop()
        start_time = loop.time()
        steps = max(1, int(duration * fps))
        interval = duration / steps
        for step in range(steps):
            # 计算插值进度 t 与数值
            t = (step + 1) / steps
            value = start + (end - start) * easing_func(t)
            # 发送参数更新
            await plugin.set_parameter_value(param, value, mode=mode)
            # 计算并 sleep 到下一个理想时刻
            now = loop.time()
            next_time = start_time + (step + 1) * interval
            sleep_time = next_time - now
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        # 最终确保到达目标值
        await plugin.set_parameter_value(param, end, mode=mode)

    @staticmethod
    def random_easing():
        """随机从常用缓动函数中选择一个，按权重分布。"""
        funcs = [
            Easing.in_out_sine,
            Easing.in_out_quad,
            Easing.in_out_back,
        ]
        weights = [0.75, 0.15, 0.1]
        return random.choices(funcs, weights=weights)[0]
