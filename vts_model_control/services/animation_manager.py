import asyncio
import inspect
import re
from typing import Dict, List

from animations.base_controller import BaseController
from configs.config import config
from services.vts_plugin import plugin
from utils.logger import logger


class AnimationManager:
    """管理所有空闲动画控制器的生命周期"""

    def __init__(self):
        self.controllers: List[BaseController] = []

    def register_idle_controller(self, controller: BaseController):
        """注册一个空闲动画控制器。"""
        self.controllers.append(controller)
        logger.info(f"已注册动画控制器: {controller.__class__.__name__}")

    async def start_all(self):
        """启动所有已注册且未在运行的动画控制器。"""
        if not self.controllers:
            logger.info("没有已注册的动画控制器, 无需启动.")
            return

        logger.info("正在启动动画控制器...")
        tasks = [controller.start() for controller in self.controllers if not controller.is_running]
        if not tasks:
            logger.info("所有已注册的动画控制器均已在运行中.")
            return

        await asyncio.gather(*tasks)
        logger.info("动画控制器启动完成.")

    async def stop_all(self):
        """立即停止所有正在运行的动画控制器，不等待当前任务完成。"""
        logger.info("正在立即停止所有动画控制器...")
        tasks = [controller.stop_without_wait() for controller in self.controllers if controller.is_running]

        if not tasks:
            logger.info("没有正在运行的动画控制器.")
            return

        await asyncio.gather(*tasks)
        logger.info("已向所有动画控制器发送停止信号.")


# 创建一个全局单例
animation_manager = AnimationManager() 