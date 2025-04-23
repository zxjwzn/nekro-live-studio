import asyncio
from animation.easing import Easing
import random

class Tweener:
    """通用的缓动工具类，用于在指定时间内平滑地更新参数值。"""
    @staticmethod
    async def tween(plugin, param: str, start: float, end: float, duration: float,
                    easing_func, mode: str = "set", fps: int = 60):
        start_time = asyncio.get_event_loop().time()
        end_time = start_time + duration
        while True:
            now = asyncio.get_event_loop().time()
            if now >= end_time:
                break
            t = max(0.0, min(1.0, (now - start_time) / duration))
            value = start + (end - start) * easing_func(t)
            await plugin.set_parameter_value(param, value, mode=mode)
            await asyncio.sleep(1 / fps)
        # 确保到达目标值
        await plugin.set_parameter_value(param, end, mode=mode)

    @staticmethod
    def random_easing():
        """随机从常用缓动函数中选择一个，按权重分布。"""
        funcs = [
            Easing.ease_in_out_sine,
            Easing.ease_in_out_sine,
            Easing.ease_in_out_quad,
            Easing.ease_in_out_back,
        ]
        weights = [0.5, 0.25, 0.15, 0.1]
        return random.choices(funcs, weights=weights)[0]

    @staticmethod
    async def tween_random(plugin, param: str, start: float, end: float, duration: float,
                            mode: str = "set", fps: int = 60):
        """使用随机选取的缓动函数执行 tween 过渡。"""
        easing_func = Tweener.random_easing()
        return await Tweener.tween(plugin, param, start, end, duration, easing_func, mode, fps) 