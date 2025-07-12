import asyncio

# 新增导入用于自动搜索和注册
import importlib
import inspect
import pkgutil
import re
from pathlib import Path
from typing import Dict, List, Optional

from ..controllers.base_controller import AnimationType, BaseController
from ..utils.logger import logger


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
                #logger.info(f"已注册空闲动画控制器: {controller.__class__.__name__}")
            elif animation_type == AnimationType.ONESHOT:
                self.oneshot_controllers.append(controller)
                #logger.info(f"已注册一次性动画控制器: {controller.__class__.__name__}")

    def auto_discover_and_register_controllers(self):
        """自动搜索并注册所有控制器"""
        logger.info("开始自动搜索和注册控制器...")
        
        # 获取控制器模块的路径
        controllers_package = "nekro_live_studio.controllers.controllers"
        controllers_path = Path(__file__).parent.parent / "controllers" / "controllers"
        
        if not controllers_path.exists():
            logger.error(f"控制器目录不存在: {controllers_path}")
            return
        
        registered_count = 0
        
        # 遍历控制器目录中的所有 Python 文件
        for file_path in controllers_path.glob("*.py"):
            if file_path.name.startswith("__") or file_path.name.startswith("test_"):
                continue
                
            module_name = file_path.stem
            full_module_name = f"{controllers_package}.{module_name}"
            
            try:
                # 动态导入模块
                module = importlib.import_module(full_module_name)
                
                # 遍历模块中的所有类
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # 检查是否是 BaseController 的子类（但不是 BaseController 本身）
                    if (obj != BaseController and 
                        issubclass(obj, BaseController) and 
                        obj.__module__ == full_module_name):
                        
                        try:
                            # 实例化控制器并注册
                            controller_instance = obj()
                            self.register_controller(controller_instance)
                            registered_count += 1
                            logger.info(f"自动注册控制器: {name} (来自 {module_name})")
                        except Exception as e:
                            logger.error(f"实例化控制器 {name} 时出错: {e}", exc_info=True)
                            
            except Exception as e:
                logger.error(f"导入模块 {full_module_name} 时出错: {e}", exc_info=True)
        
        logger.info(f"自动搜索和注册完成，共注册了 {registered_count} 个控制器")

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
                await controller.execute(*args, **kwargs)
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
