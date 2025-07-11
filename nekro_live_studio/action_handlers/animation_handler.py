import asyncio
from typing import Optional, cast

from ..schemas.actions import Action, Animation
from ..services.tweener import tweener
from ..utils.easing import Easing
from ..utils.logger import logger
from .base import ActionHandler


class AnimationHandler(ActionHandler):
    """处理 'animation' 动作的具体策略"""

    async def handle(self, action: Action, tts_start_event: Optional[asyncio.Event] = None):  # noqa: ARG002
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
