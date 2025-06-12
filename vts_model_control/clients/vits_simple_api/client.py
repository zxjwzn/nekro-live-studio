import asyncio
import io
from typing import AsyncIterator, Optional

import httpx
from configs.config import config
from services.ffmpeg import play_audio_stream_with_ffplay
from utils.logger import logger


class VITSSimpleAPIClient:
    """VITS Simple API 客户端"""

    def __init__(self):
        self.config = config.TTS
        self.base_url = self.config.HOST_AND_PORT

    async def speak(
        self,
        text: str,
        lang: str | None = None,
        speaker_id: str | None = None,
        started_event: Optional[asyncio.Event] = None,
        finished_event: Optional[asyncio.Event] = None,
        volume: Optional[float] = None,
    ) -> bool:
        """
        从文本生成语音并流式播放
        """
        try:
            audio_stream = self._generate_speech_stream(
                text=text, lang=lang, speaker_id=speaker_id,
            )
            return await play_audio_stream_with_ffplay(
                audio_stream=audio_stream,
                started_event=started_event,
                finished_event=finished_event,
                volume=volume,
            )
        except Exception as e:
            logger.error(f"播放语音时发生错误: {e}")
            if finished_event:
                finished_event.set()
            return False

    async def _generate_speech_stream(
        self,
        text: str,
        lang: str | None = None,
        speaker_id: str | None = None,
    ) -> AsyncIterator[bytes]:
        """
        调用 VITS Simple API 并以异步生成器形式返回音频流
        """
        model_name = self.config.NAME.lower()

        params = {
            "text": text,
            "id": speaker_id or self.config.SPEAKER_ID,
            "format": "wav",
            "lang": lang or self.config.VOICE_LANG,
            "streaming": "true",
        }

        request_url = f"{self.base_url}voice/{model_name}"

        try:
            async with (
                httpx.AsyncClient() as client,
                client.stream(
                    "GET",
                    request_url,
                    params=params,
                    timeout=30,
                ) as response,
            ):
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    yield chunk
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP错误: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"生成语音流时发生错误: {e}")


vits_simple_api_client = VITSSimpleAPIClient()
