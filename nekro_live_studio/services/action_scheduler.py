import asyncio
from collections import deque
from typing import Deque, Optional, cast

from ..action_handlers.animation_handler import AnimationHandler
from ..action_handlers.base import ActionHandler
from ..action_handlers.expression_handler import ExpressionHandler
from ..action_handlers.say_handler import SayHandler
from ..action_handlers.sound_play_handler import SoundPlayHandler
from ..schemas.actions import Action, Animation, Expression, Say, SoundPlay
from ..utils.logger import logger


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
        self.handlers: dict[str, ActionHandler] = {
            "say": SayHandler(),
            "animation": AnimationHandler(),
            "expression": ExpressionHandler(),
            "sound_play": SoundPlayHandler(),
        }
        self._initialized = True

    def _get_action_completion_time(self, action: Action) -> float:
        """计算单个动作的完成时间（包括延迟）"""
        # 这个方法现在变得不那么准确了，因为它不再直接访问 audio_player
        # 暂时保留，但可以考虑在未来移除或重构
        delay = getattr(action.data, "delay", 0.0)
        duration = 0.0
        action_type = action.type

        if action_type == "animation":
            anim_action = cast(Animation, action)
            duration = anim_action.data.duration
        elif action_type == "expression":
            expression_action = cast(Expression, action)
            if expression_action.data.duration > 0:
                duration = expression_action.data.duration
        elif action_type == "sound_play":
            # 无法直接获取时长，返回0
            duration = 0.0

        return delay + duration

    def add_action(self, action: Action) -> float:
        """添加动作到队列并返回其预估完成时间"""
        self.action_queue.append(action)
        logger.debug(f"动作已添加到队列: {action.type}. 队列大小: {len(self.action_queue)}")
        return self._get_action_completion_time(action)

    async def execute_queue(self, loop: int = 0):
        """执行动作队列，可选循环"""
        logger.info(f"执行动作队列, 动作数量: {len(self.action_queue)}, 循环次数: {loop}.")
        if not self.action_queue:
            return

        actions_to_run = list(self.action_queue)
        self.action_queue.clear()

        say_action_with_tts_exists = any(action.type == "say" and cast(Say, action).data.tts_text for action in actions_to_run)
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

        logger.debug("动作队列执行完成")

    async def _execute_action(self, action: Action, tts_start_event: Optional[asyncio.Event] = None):
        """执行单个动作，延迟执行并委托给对应的处理器"""
        delay = getattr(action.data, "delay", 0.0)
        if delay > 0:
            await asyncio.sleep(delay)

        logger.debug(f"执行动作: {action.type} (延迟 {delay}s)，委托给处理器...")

        handler = self.handlers.get(action.type)
        if handler:
            try:
                # 统一调用签名，传递 tts_start_event
                await handler.handle(action, tts_start_event=tts_start_event)
            except Exception as e:
                logger.error(f"执行动作 {action.type} 时处理器发生错误: {e}", exc_info=True)
        else:
            logger.warning(f"没有找到可以处理动作类型 '{action.type}' 的处理器。")

    def clear_queue(self):
        """清空动作队列"""
        self.action_queue.clear()
        logger.info("动作队列已清空")


action_scheduler = ActionScheduler()
