import asyncio
from config import config
from animation.tweener import Tweener
from animation.easing import Easing

class BreathingController:
    """呼吸控制器，使用 Tweener 实现吸气-呼气循环"""
    def __init__(self, plugin):
        self.plugin = plugin
        self.cfg = config.breathing
        self._stop_event = asyncio.Event()
        self._task = None

    async def start(self):
        """启动呼吸循环"""
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())

    async def stop(self):
        """停止呼吸循环"""
        self._stop_event.set()
        if self._task:
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self):
        while not self._stop_event.is_set():
            # 吸气阶段
            if self._stop_event.is_set():
                break
            
            await Tweener.tween(
                self.plugin,
                self.cfg.PARAMETER,
                self.cfg.MIN_VALUE,
                self.cfg.MAX_VALUE,
                self.cfg.INHALE_DURATION,
                Easing.ease_in_out_sine
            )
            #确保最终状态
            await self.plugin.set_parameter_value(self.cfg.PARAMETER, self.cfg.MAX_VALUE, mode="set")

            # 呼气阶段
            await Tweener.tween(
                self.plugin,
                self.cfg.PARAMETER,
                self.cfg.MAX_VALUE,
                self.cfg.MIN_VALUE,
                self.cfg.EXHALE_DURATION,
                Easing.ease_in_out_sine
            ) 
            #确保最终状态
            await self.plugin.set_parameter_value(self.cfg.PARAMETER, self.cfg.MIN_VALUE, mode="set")
