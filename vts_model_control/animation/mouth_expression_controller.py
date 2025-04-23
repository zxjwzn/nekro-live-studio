import asyncio
import random
from config import config
from animation.tweener import Tweener
from animation.easing import Easing
from utils.logger import logger
class MouthExpressionController:
    """嘴部表情控制器，使用 Tweener 实现随机嘴部表情变化循环"""
    def __init__(self, plugin):
        self.plugin = plugin
        self.cfg = config.mouth_expression
        self._stop_event = asyncio.Event()
        self._task = None
        # 当前表情状态
        self._current_smile = 0.0
        self._current_open = 0.0

    async def start(self):
        """启动嘴部表情循环"""
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self):
        """停止嘴部表情循环"""
        self._stop_event.set()
        if self._task:
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self):
        while not self._stop_event.is_set():
            # 随机生成新表情目标
            new_smile = random.uniform(self.cfg.SMILE_MIN, self.cfg.SMILE_MAX)
            new_open = random.uniform(self.cfg.OPEN_MIN, self.cfg.OPEN_MAX)
            duration = random.uniform(self.cfg.CHANGE_MIN_DURATION, self.cfg.CHANGE_MAX_DURATION)
            logger.info(f"随机表情参数: 当前表情=(微笑:{self._current_smile:.2f}, 开口:{self._current_open:.2f}), "
                    f"目标=(微笑:{new_smile:.2f}, 开口:{new_open:.2f}), "
                    f"持续时间={duration:.2f}s, 缓动函数={Easing.ease_in_out_sine.__name__}")
            # 并行动画过渡
            await asyncio.gather(
                Tweener.tween(
                    self.plugin,
                    self.cfg.SMILE_PARAMETER,
                    self._current_smile,
                    new_smile,
                    duration,
                    Easing.ease_in_out_sine
                ),
                Tweener.tween(
                    self.plugin,
                    self.cfg.OPEN_PARAMETER,
                    self._current_open,
                    new_open,
                    duration,
                    Easing.ease_in_out_sine
                ),
            )
            #确保最终状态
            await asyncio.gather(
                self.plugin.set_parameter_value(self.cfg.SMILE_PARAMETER, new_smile, mode="set"),
                self.plugin.set_parameter_value(self.cfg.OPEN_PARAMETER, new_open, mode="set")
            )

            # 更新当前表情状态
            self._current_smile = new_smile
            self._current_open = new_open 