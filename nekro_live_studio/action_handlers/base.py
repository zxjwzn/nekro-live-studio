import asyncio
from abc import ABC, abstractmethod
from typing import Optional

from ..schemas.actions import Action


class ActionHandler(ABC):
    """所有动作处理器的抽象基类 (策略接口)"""

    @abstractmethod
    async def handle(self, action: Action, tts_start_event: Optional[asyncio.Event] = None):
        """
        执行具体的动作逻辑。
        
        Args:
            action: 包含动作类型和数据的完整 Action 对象。
        """
