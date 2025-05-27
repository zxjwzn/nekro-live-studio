import asyncio
import json
from typing import List, Dict, Any, Optional
import time

from configs.config import config
from services.tweener import Tweener
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
        
    def register_idle_controller(self, controller, skip_pause: bool = False):
        """注册空闲动画控制器，可通过 skip_pause=True 设置此控制器在暂停时被跳过"""
        controller.skip_pause = skip_pause
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
            # 跳过标记为 skip_pause 的控制器
            if getattr(ctrl, "skip_pause", False):
                continue
            await ctrl.stop_without_wait()
        logger.info("空闲动画已暂停")
    
    async def resume_idle_animations(self):
        """恢复所有空闲动画"""
        if self.is_idle_running:
            return
            
        self.is_idle_running = True
        for ctrl in self.idle_controllers:
            # 跳过标记为 skip_pause 的控制器
            if getattr(ctrl, "skip_pause", False):
                continue
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
                    action_type = action.get("type", "animation") # 默认为 animation 类型

                    if action_type == "animation":
                        parameter = action.get("parameter")
                        start_val = action.get("from")
                        end_val = action.get("to")
                        duration = action.get("duration", 1.0)
                        startTime = action.get("startTime", 0.0)
                        easing_name = action.get("easing", "linear")
                        
                        if parameter is None:
                            logger.warning(f"动画动作缺少 'parameter' 字段: {action}")
                            continue

                        # 获取起始值
                        if start_val is None:
                            param_info = await plugin.get_parameter_value(parameter)
                            start_val = param_info.get("value", 0.0)
                        # 缓动函数
                        easing_func = getattr(Easing, easing_name, None) or Easing.linear
                        
                        async def anim_task_fn(param=parameter, s=start_val, e=end_val, d=duration, ef=easing_func, st=startTime):
                            try:
                                if st > 0:
                                    await asyncio.sleep(st)
                                await Tweener.tween(plugin, param, s, e, d, ef)
                            except asyncio.CancelledError:
                                pass # 任务被取消时静默处理
                            except Exception as ex_anim:
                                logger.error(f"执行参数动画 '{param}' 时出错: {ex_anim}")
                        tasks.append(asyncio.create_task(anim_task_fn()))
                    
                    elif action_type == "emotion":
                        emotion_name = action.get("name")
                        # VTube Studio API 使用 expressionFile, 我们在 action 中用 name
                        duration = action.get("duration", 0.0) # 0 或负数表示永久，除非被后续动作或取消覆盖
                        startTime = action.get("startTime", 0.0)
                        fade_time = action.get("fadeTime", config.plugin.expression_fade_time) # 从配置中读取默认表情淡入淡出时间

                        if not emotion_name:
                            logger.warning(f"表情动作缺少 'name' (expressionFile) 字段: {action}")
                            continue

                        async def emotion_task_fn(name=emotion_name, dur=duration, st=startTime, ft=fade_time):
                            try:
                                if st > 0:
                                    await asyncio.sleep(st)
                                
                                logger.info(f"激活表情: {name}, 淡入时间: {ft}s")
                                await plugin.activate_expression(expression_file=name, active=True, fade_time=ft)

                                if dur > 0: # 只有当持续时间明确大于0时，才在之后停用
                                    await asyncio.sleep(dur)
                                    logger.info(f"根据持续时间停用表情: {name} (原定持续时间: {dur}s), 淡出时间: {ft}s")
                                    await plugin.activate_expression(expression_file=name, active=False, fade_time=ft)
                                # 如果 duration <= 0，表情将保持激活状态，直到被其他方式改变或插件停止
                                    
                            except asyncio.CancelledError:
                                logger.info(f"表情任务 ({name}) 被取消。")
                                # 尝试停用被取消的表情，以防其保持激活状态
                                try:
                                    logger.info(f"尝试在取消后停用表情: {name}")
                                    await plugin.activate_expression(expression_file=name, active=False, fade_time=0) # 快速停用
                                except Exception as e_cancel_deactivate:
                                    logger.warning(f"取消表情任务 ({name}) 后尝试停用时出错: {e_cancel_deactivate}")
                            except Exception as ex_emotion:
                                logger.error(f"执行表情动作 '{name}' 时出错: {ex_emotion}")
                        tasks.append(asyncio.create_task(emotion_task_fn()))
                    
                    # 可以根据需要添加其他 action_type 的处理，例如 "say"
                    # elif action_type == "say":
                    # pass # 在这里添加 say 动作的处理逻辑

                if tasks:
                    await asyncio.gather(*tasks)
                
                if loop_count > 0:
                    current_loop += 1
                else: # loop 为0或负数表示不循环（或只执行一次）
                    break # 完成一次后退出循环
            return True
        except Exception as e:
            logger.error(f"运行动画序列时发生意外错误: {e}")
            return False