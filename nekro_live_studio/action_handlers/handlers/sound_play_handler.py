import asyncio
from typing import Optional, cast

from ...schemas.actions import Action, SoundPlay
from ...services.audio_player import audio_player
from ..base import ActionHandler


class SoundPlayHandler(ActionHandler):
    """处理 'sound_play' 动作的具体策略"""

    async def handle(self, action: Action, tts_start_event: Optional[asyncio.Event] = None):  # noqa: ARG002
        sound_action = cast(SoundPlay, action)
        audio_player.play(sound_action.data)
