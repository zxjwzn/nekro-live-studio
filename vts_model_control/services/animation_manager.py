import asyncio
import json
from typing import List, Dict, Any, Optional
import time

from configs.config import config
from utils.tweener import Tweener
from utils.easing import Easing
from utils.logger import logger
from services.plugin import plugin

class AnimationManager:
    """动画管理器，负责协调空闲动画和API请求的动画"""
    
    def __init__(self):
        self.idle_controllers = []  # 空闲动画控制器列表
        self.is_idle_running = True  # 是否运行空闲动画
        self.last_api_call_time = 0  # 最后一次API调用时间
        self._resume_idle_task = None  # 恢复空闲动画的任务
        self._stop_event = asyncio.Event()
        
    def register_idle_controller(self, controller):
        """注册空闲动画控制器"""
        self.idle_controllers.append(controller)
        
    async def start(self):
        """启动动画管理器"""
        self._stop_event.clear()
        self.is_idle_running = True
        for ctrl in self.idle_controllers:
            await ctrl.start()
        self._resume_idle_task = asyncio.create_task(self._check_resume_idle())
        logger.info("动画管理器已启动")
        
    async def stop(self):
        """停止动画管理器"""
        self._stop_event.set()
        if self._resume_idle_task:
            self._resume_idle_task.cancel()
            try:
                await self._resume_idle_task
            except asyncio.CancelledError:
                pass
        for ctrl in self.idle_controllers:
            await ctrl.stop_without_wait()
        logger.info("动画管理器已停止")
    
    async def pause_idle_animations(self):
        """暂停所有空闲动画"""
        if not self.is_idle_running:
            return
            
        self.is_idle_running = False
        for ctrl in self.idle_controllers:
            await ctrl.stop_without_wait()
        logger.info("空闲动画已暂停")
    
    async def resume_idle_animations(self):
        """恢复所有空闲动画"""
        if self.is_idle_running:
            return
            
        self.is_idle_running = True
        for ctrl in self.idle_controllers:
            await ctrl.start()
        logger.info("空闲动画已恢复")
    
    async def _check_resume_idle(self):
        """定期检查是否需要恢复空闲动画，基于超时等待减少唤醒次数"""
        while True:
            try:
                # 等待停止事件，超时后 TimeoutError 用于恢复动画
                await asyncio.wait_for(self._stop_event.wait(), timeout=config.api.timeout)
                # 收到停止信号，则退出
                break
            except asyncio.TimeoutError:
                # 超时，说明最近未有 API 调用
                if not self.is_idle_running:
                    logger.info(f"{config.api.timeout}秒内没有API调用，恢复空闲动画")
                    await self.resume_idle_animations()
    
    async def run_animation(self, animation_data: Dict[str, Any]):
        """运行自定义动画
        
        Args:
            animation_data: 包含动画信息的字典，格式与animate.json相同
        """
        self.last_api_call_time = time.time()
        
        if self.is_idle_running:
            await self.pause_idle_animations()
        
        actions = animation_data.get("actions", [])
        loop_count = animation_data.get("loop", 0)
        current_loop = 0
        
        try:
            while current_loop == 0 or current_loop < loop_count:
                tasks = []
                for action in actions:
                    parameter = action.get("parameter")
                    start_val = action.get("from")
                    end_val = action.get("to")
                    duration = action.get("duration", 1.0)
                    delay = action.get("delay", 0.0)
                    easing_name = action.get("easing", "linear")
                    # 获取起始值
                    if start_val is None:
                        param_info = await plugin.get_parameter_value(parameter)
                        start_val = param_info.get("value", 0.0)
                    # 缓动函数
                    easing_func = getattr(Easing, easing_name, None) or Easing.linear
                    # 定义单任务逻辑
                    async def anim_task_fn(param=parameter, s=start_val, e=end_val, d=duration, ef=easing_func, dl=delay):
                        try:
                            if dl > 0:
                                await asyncio.sleep(dl)
                            await Tweener.tween(plugin, param, s, e, d, ef)
                        except asyncio.CancelledError:
                            pass
                    tasks.append(asyncio.create_task(anim_task_fn()))
                # 等待所有动画完成
                if tasks:
                    await asyncio.gather(*tasks)
                # 循环次数更新
                if loop_count > 0:
                    current_loop += 1
                else:
                    break
            return True
        except Exception as e:
            logger.error(f"运行动画时出错: {e}")
            return False
            
    async def _delayed_animation(self, delay_task, anim_task):
        """延迟执行动画任务"""
        await delay_task
        await anim_task 