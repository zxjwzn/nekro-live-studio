import asyncio
import inspect
import re
from typing import Dict, List, Optional

from controllers.base_controller import AnimationType, BaseController
from utils.logger import logger


class AnimationManager:
    """管理所有动画控制器的生命周期"""

    def __init__(self):
        self.idle_controllers: List[BaseController] = []
        self.oneshot_controllers: List[BaseController] = []

    def register_controller(self, controller: BaseController):
        """注册一个动画控制器到对应的类型列表中。"""
        if controller.config.ENABLED is False:
            return

        animation_type = controller.get_animation_type()
        if controller not in self.oneshot_controllers:
            if animation_type == AnimationType.IDLE:
                self.idle_controllers.append(controller)
                logger.info(f"已注册空闲动画控制器: {controller.__class__.__name__}")
            elif animation_type == AnimationType.ONESHOT:
                self.oneshot_controllers.append(controller)
                logger.info(f"已注册一次性动画控制器: {controller.__class__.__name__}")

    def get_controller_by_name(self, controller_name: str) -> Optional[BaseController]:
        """通过控制器名获取控制器实例
        
        Args:
            controller_name: 控制器类名
            
        Returns:
            匹配的控制器实例，如果没有找到则返回 None
        """
        all_controllers = self.idle_controllers + self.oneshot_controllers
        
        for controller in all_controllers:
            if controller.__class__.__name__ == controller_name:
                return controller
        
        logger.warning(f"没有找到控制器: {controller_name}")
        return None

    async def start_all_idle(self):
        """启动所有已注册且未在运行的空闲动画控制器。"""
        if not self.idle_controllers:
            logger.info("没有已注册的空闲动画控制器, 无需启动.")
            return

        logger.info("正在启动空闲动画控制器...")
        tasks = [controller.start() for controller in self.idle_controllers if not controller.is_running]
        if not tasks:
            logger.info("所有已注册的空闲动画控制器均已在运行中.")
            return

        await asyncio.gather(*tasks)
        logger.info("空闲动画控制器启动完成.")

    async def pause_idle(self):
        """暂停正在运行的空闲动画控制器"""
        logger.info("正在暂停所有空闲动画控制器...")
        tasks = []
        for controller in self.idle_controllers:
            if controller.is_running:
                tasks.append(controller.stop_without_wait())

        if not tasks:
            logger.info("没有正在运行的空闲动画控制器.")
            return

        await asyncio.gather(*tasks)
        logger.info("已向所有空闲动画控制器发送停止信号.")

    async def execute_oneshot(self, animation_name: str, *args, **kwargs):
        """执行一次性动画"""
        controller = self.get_controller_by_name(animation_name)
        if controller:
            if not controller.is_running:
                await controller.start(*args, **kwargs)
            else:
                logger.warning(f"一次性动画 {animation_name} 正在运行中，跳过执行")
        else:
            logger.warning(f"没有找到一次性动画控制器: {animation_name}")

    async def stop_animation_without_wait(self, animation_name: str):
        """立即停止一个动画控制器，不等待当前任务完成。"""
        all_controllers = self.idle_controllers + self.oneshot_controllers

        for controller in all_controllers:
            if controller.__class__.__name__ == animation_name:
                await controller.stop_without_wait()
                return
        logger.warning(f"没有找到动画控制器: {animation_name}")

    async def stop_all_idle(self):
        """立即停止所有正在运行的空闲动画控制器，不等待当前任务完成。"""
        logger.info("正在立即停止所有空闲动画控制器...")
        tasks = [controller.stop_without_wait() for controller in self.idle_controllers if controller.is_running]

        if not tasks:
            logger.info("没有正在运行的空闲动画控制器.")
            return

        await asyncio.gather(*tasks)
        logger.info("已向所有空闲动画控制器发送停止信号.")


# 创建一个全局单例
controller_manager = AnimationManager()
