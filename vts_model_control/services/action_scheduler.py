import asyncio
from collections import deque
from typing import Deque, Optional, cast

from configs.config import config
from schemas.actions import Action, Animation, Emotion, Say, SoundPlay, SoundPlayData
from services.animation_manager import animation_manager
from services.audio_player import audio_player
from services.subtitle_broadcaster import subtitle_broadcaster
from services.tweener import tweener
from services.vts_plugin import plugin
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
        self._initialized = True

    def add_action(self, action: Action):
        """添加动作到队列"""
        self.action_queue.append(action)
        logger.info(f"动作已添加到队列: {action.type}. 队列大小: {len(self.action_queue)}")

    async def execute_queue(self, loop: int = 0):
        """执行动作队列，可选循环"""
        logger.info(f"执行动作队列, 动作数量: {len(self.action_queue)}, 循环次数: {loop}.")
        if not self.action_queue:
            return
        await animation_manager.stop_all()
        actions_to_run = list(self.action_queue)
        self.action_queue.clear()

        total_runs = loop + 1
        for i in range(total_runs):
            logger.info(f"执行第 {i + 1} 次, 共 {total_runs} 次")
            tasks = []
            for action in actions_to_run:
                tasks.append(asyncio.create_task(self._execute_action(action)))

            if tasks:
                await asyncio.gather(*tasks)
        
        logger.info(f"动作队列执行完成, 共执行 {total_runs} 次")
        await animation_manager.start_all()

    async def _execute_action(self, action: Action):
        """执行单个动作，延迟执行"""
        delay = getattr(action.data, "delay", 0.0)
        if delay > 0:
            await asyncio.sleep(delay)

        action_type = action.type
        logger.info(f"执行动作: {action_type} 延迟 {delay}s")

        try:
            if action_type == "say":
                say_action = cast(Say, action)
                # 广播完整字幕信息
                await subtitle_broadcaster.broadcast(say_action.model_dump_json())
                for text, speed in zip(say_action.data.text, say_action.data.speed):
                    wait_time = 1 / speed
                    for _ in text:
                        data = SoundPlayData(path=config.SPEECH_SYNTHESIS.AUDIO_FILE_PATH, volume=config.SPEECH_SYNTHESIS.VOLUME, speed=1.0, duration=0.0, delay=0.0) 
                        audio_player.play(data)
                        await asyncio.sleep(wait_time)

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
                )

            elif action_type == "emotion":
                emotion_action = cast(Emotion, action)
                if emotion_action.data.name:
                    await plugin.activate_expression(expression_file=emotion_action.data.name, active=True)
                    if emotion_action.data.duration > 0:
                        await asyncio.sleep(emotion_action.data.duration)
                        await plugin.activate_expression(expression_file=emotion_action.data.name, active=False)

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
