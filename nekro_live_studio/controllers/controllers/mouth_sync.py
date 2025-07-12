import asyncio
import random
from typing import Optional, Type

from ...services.tweener import tweener
from ...utils.easing import Easing
from ...utils.logger import logger
from ..base_controller import OneShotController
from ..config import MouthSyncConfig
from ..config_manager import config_manager


class MouthSyncController(OneShotController[MouthSyncConfig]):
    """根据音频响度控制嘴部开合的控制器"""

    @property
    def config(self) -> MouthSyncConfig:
        return config_manager.config.mouth_sync

    async def execute(self, loudness_queue: asyncio.Queue[Optional[float]]):
        logger.info("启动嘴型同步...")
        try:
            while True:
                lufs = await loudness_queue.get()
                logger.debug(f"响度: {lufs}")
                if lufs is None:  # End of stream
                    break

                target_open = self.config.OPEN_MIN
                if lufs >= self.config.LOUDNESS_THRESHOLD:
                    target_open = random.uniform(self.config.OPEN_MIN, self.config.OPEN_MAX)

                await tweener.tween(
                    param=self.config.OPEN_PARAMETER,
                    end=target_open,
                    duration=0.05, #0.06 0.07都会提前结束
                    easing_func=Easing.linear,
                    priority=2,  # 高优先级以覆盖其他可能影响嘴部的动画
                )
                await asyncio.sleep(0.05)

        except asyncio.CancelledError:
            logger.info("嘴型同步任务被取消.")
        finally:
            logger.info("嘴型同步结束, 闭合嘴巴.")
            await tweener.tween(
                param=self.config.OPEN_PARAMETER,
                end=self.config.OPEN_MIN,
                duration=0.2,
                easing_func=Easing.out_quad,
                priority=2,
            )


mouth_sync_controller = MouthSyncController()
