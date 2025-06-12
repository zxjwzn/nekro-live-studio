import asyncio
from collections import deque
from typing import Deque, Optional, cast

from clients.vits_simple_api.client import vits_simple_api_client
from clients.vtuber_studio.plugin import plugin
from configs.config import config
from schemas.actions import Action, Animation, Expression, Say, SoundPlay, SoundPlayData
from services.audio_player import audio_player
from services.controller_manager import controller_manager
from services.subtitle_broadcaster import subtitle_broadcaster
from services.tweener import tweener
from utils.easing import Easing
from utils.logger import logger


class ActionScheduler:
    _instance: Optional["ActionScheduler"] = None

    def __new__(cls) -> "ActionScheduler":
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.action_queue: Deque[Action] = deque()
        self.tts_lock = asyncio.Lock()
        self._initialized = True

    def _get_action_completion_time(self, action: Action) -> float:
        """计算单个动作的完成时间（包括延迟）"""
        delay = getattr(action.data, "delay", 0.0)
        duration = 0.0
        action_type = action.type

        if action_type == "animation":
            anim_action = cast(Animation, action)
            duration = anim_action.data.duration
        elif action_type == "expression":
            expression_action = cast(Expression, action)
            # duration <= 0 表示永久，这里当做0时长处理
            if expression_action.data.duration > 0:
                duration = expression_action.data.duration
        elif action_type == "sound_play":
            sound_action = cast(SoundPlay, action)
            duration = audio_player.get_duration(sound_action.data)

        return delay + duration

    def add_action(self, action: Action) -> float:
        """添加动作到队列并返回其预估完成时间"""
        self.action_queue.append(action)
        logger.info(f"动作已添加到队列: {action.type}. 队列大小: {len(self.action_queue)}")
        return self._get_action_completion_time(action)

    async def execute_queue(self, loop: int = 0):
        """执行动作队列，可选循环"""
        logger.info(f"执行动作队列, 动作数量: {len(self.action_queue)}, 循环次数: {loop}.")
        if not self.action_queue:
            return

        actions_to_run = list(self.action_queue)
        self.action_queue.clear()

        # 检查队列中是否存在带TTS的SayAction，以同步所有动作
        say_action_with_tts_exists = any(
            action.type == "say" and cast(Say, action).data.tts_text for action in actions_to_run
        )
        # 如果没有TTS任务，立即暂停空闲动画
        if not say_action_with_tts_exists:
            await controller_manager.pause()

        tts_start_event = asyncio.Event() if say_action_with_tts_exists else None

        total_runs = loop + 1
        for i in range(total_runs):
            logger.info(f"执行第 {i + 1} 次, 共 {total_runs} 次")
            if tts_start_event:
                tts_start_event.clear()

            tasks = []
            for action in actions_to_run:
                tasks.append(asyncio.create_task(self._execute_action(action, tts_start_event)))

            if tasks:
                await asyncio.gather(*tasks)

        logger.info(f"动作队列执行完成, 共执行 {total_runs} 次")
        await controller_manager.start_all()

    async def _execute_action(self, action: Action, tts_start_event: Optional[asyncio.Event] = None):
        """执行单个动作，延迟执行"""
        action_type = action.type
        is_say_with_tts = action_type == "say" and cast(Say, action).data.tts_text

        # 如果有TTS任务，并且当前任务不是那个TTS任务，则等待TTS开始信号
        if tts_start_event and not is_say_with_tts:
            logger.info(f"动作 {action.type} 等待 TTS 开始...")
            await tts_start_event.wait()
            #logger.info(f"TTS 已开始, 动作 {action.type} 继续执行.")

        delay = getattr(action.data, "delay", 0.0)
        if delay > 0:
            await asyncio.sleep(delay)

        logger.info(f"执行动作: {action_type} 延迟 {delay}s")

        try:
            if action_type == "say":
                say_action = cast(Say, action)

                if say_action.data.tts_text:
                    async with self.tts_lock:

                        local_start_event = asyncio.Event()
                        finished_event = asyncio.Event()

                        # 第一个获取锁的 say 动作将负责触发全局事件
                        is_first_tts_runner = tts_start_event and not tts_start_event.is_set()

                        # 在后台播放音频, 传递的是局部事件
                        speak_task = asyncio.create_task(
                            vits_simple_api_client.speak(
                                text=say_action.data.tts_text,
                                started_event=local_start_event,
                                finished_event=finished_event,
                                volume=say_action.data.volume,
                            ),
                        )

                        # 等待这个动作自己的音频开始, 或是在开始前就失败
                        done, pending = await asyncio.wait(
                            [local_start_event.wait(), finished_event.wait()],
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        for task in pending:
                            task.cancel()

                        # 如果任务在开始前就失败了, 中止动作
                        if finished_event.is_set() and not local_start_event.is_set():
                            logger.error("TTS 播放任务在开始前就已失败, 中止 'say' 动作.")
                            await speak_task  # 等待任务完成以获取可能的异常信息
                            return

                        # 音频已开始, 如果是第一个, 则触发全局事件并暂停空闲动画
                        if is_first_tts_runner:
                            await controller_manager.pause()
                            if tts_start_event:
                                tts_start_event.set()

                        logger.info("音频已开始播放, 开始显示字幕...")
                        await subtitle_broadcaster.broadcast(say_action.model_dump_json())

                        # 等待音频播放完成
                        await finished_event.wait()
                        logger.info("音频播放完毕, 发送完成消息.")
                        await subtitle_broadcaster.broadcast('{"type": "finished"}')
                        await speak_task  # 确保后台任务最终完成
                else:
                    # 如果没有 tts_text，则只广播字幕
                    await subtitle_broadcaster.broadcast(say_action.model_dump_json())

            elif action_type == "animation":
                anim_action = cast(Animation, action)
                easing_func_name = anim_action.data.easing
                easing_func = getattr(Easing, easing_func_name, Easing.linear)
                if not hasattr(Easing, easing_func_name):
                    logger.warning(f"缓动函数 '{easing_func_name}' 未找到. 回退到线性缓动.")

                await tweener.tween(
                    param=anim_action.data.parameter,
                    start=anim_action.data.from_value,
                    end=anim_action.data.target,
                    duration=anim_action.data.duration,
                    easing_func=easing_func,
                    priority=max(anim_action.data.priority, 1),
                )

            elif action_type == "expression":
                expression_action = cast(Expression, action)
                if expression_action.data.name:
                    await plugin.activate_expression(expression_file=expression_action.data.name, active=True)
                    if expression_action.data.duration > 0:
                        await asyncio.sleep(expression_action.data.duration)
                        await plugin.activate_expression(expression_file=expression_action.data.name, active=False)

            elif action_type == "sound_play":
                sound_action = cast(SoundPlay, action)
                audio_player.play(sound_action.data)

        except Exception as e:
            logger.error(f"执行动作 {action_type} 时发生错误: {e}", exc_info=True)

    def clear_queue(self):
        """清空动作队列"""
        self.action_queue.clear()
        logger.info("动作队列已清空")


action_scheduler = ActionScheduler()
