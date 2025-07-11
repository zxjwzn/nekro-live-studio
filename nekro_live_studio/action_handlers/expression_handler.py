import asyncio
from typing import Optional, cast

from ..clients.vtuber_studio.plugin import plugin
from ..schemas.actions import Action, Expression
from .base import ActionHandler


class ExpressionHandler(ActionHandler):
    """处理 'expression' 动作的具体策略"""

    async def handle(self, action: Action, tts_start_event: Optional[asyncio.Event] = None):  # noqa: ARG002
        expression_action = cast(Expression, action)
        if expression_action.data.name:
            await plugin.activate_expression(expression_file=expression_action.data.name, active=True)
            if expression_action.data.duration > 0:
                await asyncio.sleep(expression_action.data.duration)
                await plugin.activate_expression(expression_file=expression_action.data.name, active=False)
