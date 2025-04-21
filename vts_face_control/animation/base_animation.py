import asyncio
import logging
import random
from typing import Optional, Dict, Any, Callable

from vts_client import VTSPlugin, APIError, ResponseError, ConnectionError

class BaseAnimation:
    """所有动画效果的基类"""
    
    def __init__(self, plugin: VTSPlugin, config: Dict[str, Any], logger: logging.Logger):
        self.plugin = plugin
        self.config = config
        self.logger = logger
        self.active = False
        self.task: Optional[asyncio.Task] = None
        self.current_values = {}  # 存储当前参数值
    
    async def start(self):
        """启动动画任务"""
        if self.active:
            return
        
        self.active = True
        self.task = asyncio.create_task(self.animation_task())
        self.logger.info(f"已启动 {self.__class__.__name__} 效果")
    
    async def stop(self):
        """停止动画任务"""
        if not self.active:
            return
            
        self.active = False
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        self.logger.info(f"已停止 {self.__class__.__name__} 效果")
    
    async def animation_task(self):
        """主动画循环任务，子类必须实现此方法"""
        raise NotImplementedError("子类必须实现animation_task方法")
    
    async def animation_cycle(self):
        """单个动画周期，子类必须实现此方法"""
        raise NotImplementedError("子类必须实现animation_cycle方法")
    
    async def transition_parameter(
            self, 
            parameter_name: str, 
            start_value: float, 
            end_value: float, 
            duration: float, 
            easing_func: Callable[[float], float],
            mode: str = "set"
        ):
        """通用参数过渡动画方法"""
        start_time = asyncio.get_event_loop().time()
        end_time = start_time + duration
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time >= end_time:
                break
                
            # 计算进度比例
            elapsed = current_time - start_time
            progress = min(1.0, elapsed / duration)
            
            # 使用缓动函数计算当前值
            eased_progress = easing_func(progress)
            value = start_value + (end_value - start_value) * eased_progress
            
            try:
                await self.plugin.set_parameter_value(parameter_name, value, mode=mode)
                self.current_values[parameter_name] = value
            except (APIError, ResponseError, ConnectionError) as e:
                self.logger.error(f"设置参数 {parameter_name} 时出错: {e}")
                return False
                
            # 控制更新频率
            next_step_time = min(current_time + 0.016, end_time)  # 约60fps
            sleep_time = max(0, next_step_time - asyncio.get_event_loop().time())
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # 确保到达目标值
        try:
            await self.plugin.set_parameter_value(parameter_name, end_value, mode=mode)
            self.current_values[parameter_name] = end_value
        except (APIError, ResponseError, ConnectionError) as e:
            self.logger.error(f"设置参数 {parameter_name} 最终值时出错: {e}")
            return False
            
        return True
        
    def choose_random_easing(self, natural_movement=True):
        """选择一个随机的缓动函数"""
        from utils.easing import (
            ease_in_out_sine, ease_in_out_quad, 
            ease_in_out_cubic, ease_in_out_back
        )
        
        if natural_movement:
            # 偏向于使用更自然的缓动函数
            easing_funcs = [
                ease_in_out_sine,
                ease_in_out_sine,
                ease_in_out_quad,
                ease_in_out_back,
            ]
            weights = [0.5, 0.25, 0.15, 0.1]
            return random.choices(easing_funcs, weights=weights)[0]
        else:
            # 所有缓动函数等概率选择
            easing_funcs = [
                ease_in_out_sine, ease_in_out_quad, 
                ease_in_out_cubic, ease_in_out_back
            ]
            return random.choice(easing_funcs)