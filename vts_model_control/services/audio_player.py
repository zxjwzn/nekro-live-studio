import asyncio
import io
import os
from pathlib import Path
from typing import AsyncIterator, Dict, Optional

import pygame
from configs.config import config
from pydub import AudioSegment
from schemas.actions import SoundPlayData
from utils.logger import logger


class AudioPlayer:
    _instance: Optional["AudioPlayer"] = None

    def __new__(cls, *args, **kwargs) -> "AudioPlayer":  # noqa: ARG004
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, base_audio_path: str = "data/resources/audios"):
        if hasattr(self, "_initialized") and self._initialized:
            return

        pygame.mixer.init(channels=30)
        pygame.mixer.set_num_channels(30)
        self.base_audio_path = Path(base_audio_path)
        self.base_audio_path.mkdir(parents=True, exist_ok=True)
        self.playing_sounds: Dict[int, pygame.mixer.Channel] = {}
        self._next_id: int = 0  # ID计数器，从0开始
        self._initialized = True

    def _resolve_path(self, file_path: str) -> Optional[Path]:
        path = Path(file_path)
        if path.is_absolute():
            if path.exists():
                return path
        else:
            relative_path = self.base_audio_path / path
            if relative_path.exists():
                return relative_path

        logger.error(f"Audio file not found: {file_path}")
        return None

    def _get_next_id(self) -> int:
        """获取下一个可用的ID"""
        current_id = self._next_id
        self._next_id += 1
        return current_id

    def get_duration(self, sound_data: SoundPlayData) -> float:
        """获取音频的播放时长（秒），考虑播放速度。如果文件未找到或出错，则返回0。"""
        file_path = self._resolve_path(sound_data.path)
        if not file_path:
            return 0.0

        try:
            audio = AudioSegment.from_file(file_path)
            return audio.duration_seconds / sound_data.speed
        except Exception as e:
            logger.error(f"Error getting duration for audio {sound_data.path}: {e}")
            return 0.0

    async def play_from_stream(
        self,
        stream_iterator: AsyncIterator[bytes],
        started_event: Optional[asyncio.Event] = None,
        finished_event: Optional[asyncio.Event] = None,
        volume: Optional[float] = None,
    ) -> bool:
        """
        从音频流实时播放音频。
        使用 ffplay 子进程。需要系统安装 ffmpeg。
        """
        final_volume = config.TTS.VOLUME if volume is None else volume
        # 将音量从 0.0-1.0 转换为 ffplay 使用的 0-100
        ffplay_volume = int(max(0.0, final_volume) * 100)

        ffplay_cmd = ["ffplay", "-autoexit", "-nodisp", "-i", "-", "-volume", str(ffplay_volume)]
        try:
            proc = await asyncio.create_subprocess_exec(
                *ffplay_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            logger.error("`ffplay` 未找到。如需使用流式播放，请安装 ffmpeg 并将其添加到系统 PATH 中。")
            return False

        if proc.stdin is None or proc.stderr is None:
            logger.error("无法获取 ffplay 进程的 stdin/stderr。")
            return False

        stderr = proc.stderr

        async def log_stderr():
            while line := await stderr.readline():
                logger.debug(f"ffplay: {line.decode().strip()}")

        log_task = asyncio.create_task(log_stderr())

        try:
            async for chunk in stream_iterator:
                if proc.stdin.is_closing():
                    logger.warning("ffplay 的 stdin 已关闭，停止写入音频流。")
                    break
                proc.stdin.write(chunk)
                if started_event :
                    started_event.set()
                await proc.stdin.drain()
        except Exception as e:
            logger.error(f"向 ffplay 传输音频流时发生错误: {e}")
            if proc.returncode is None:
                proc.kill()
            return False
        finally:
            if not proc.stdin.is_closing():
                proc.stdin.close()
            await proc.wait()
            log_task.cancel()
            if finished_event:
                finished_event.set()
            logger.info(f"ffplay 进程已结束，返回码: {proc.returncode}")

        if proc.returncode != 0:
            logger.error(f"ffplay 异常退出，返回码: {proc.returncode}")
            return False

        return True

    def play_from_buffer(self, buffer: io.BytesIO, volume: float = 1.0, speed: float = 1.0) -> Optional[int]:
        """从内存缓冲区播放音频，返回播放ID，失败时返回None"""
        try:
            buffer.seek(0)
            audio = AudioSegment.from_file(buffer)

            if speed != 1.0:
                audio = audio.speedup(playback_speed=speed)

            # Pygame需要一个新的缓冲区来播放，所以我们再次导出
            play_buffer = io.BytesIO()
            audio.export(play_buffer, format="wav")
            play_buffer.seek(0)

            sound = pygame.mixer.Sound(play_buffer)
            sound.set_volume(volume)

            channel = sound.play()

            if channel:
                play_id = self._get_next_id()
                self.playing_sounds[play_id] = channel
                return play_id

            logger.error("无法播放音频.")
            return None  # noqa: TRY300

        except Exception as e:
            logger.error(f"播放音频时发生错误: {e}")
            return None

    def play(self, sound_data: SoundPlayData) -> Optional[int]:
        """播放音频，返回播放ID，失败时返回None"""
        file_path = self._resolve_path(sound_data.path)
        if not file_path:
            return None

        try:
            audio = AudioSegment.from_file(file_path)

            if sound_data.speed != 1.0:
                audio = audio.speedup(playback_speed=sound_data.speed)

            buffer = io.BytesIO()
            audio.export(buffer, format="wav")
            buffer.seek(0)

            sound = pygame.mixer.Sound(buffer)
            sound.set_volume(sound_data.volume)

            maxtime = int(sound_data.duration * 1000) if sound_data.duration > 0 else 0
            channel = sound.play(maxtime=maxtime)

            if channel:
                play_id = self._get_next_id()
                self.playing_sounds[play_id] = channel
                return play_id
            logger.error(f"Could not play {sound_data.path}: No available audio channels.")
            return None  # noqa: TRY300

        except Exception as e:
            logger.error(f"Error playing audio {sound_data.path}: {e}")
            return None

    def stop(self, play_id: int) -> bool:
        """根据ID停止特定的音频播放，成功返回True，失败返回False"""
        channel = self.playing_sounds.pop(play_id, None)
        if channel and channel.get_busy():
            channel.stop()
            return True
        return False

    def stop_all(self) -> None:
        """停止所有音频播放"""
        pygame.mixer.stop()
        self.playing_sounds.clear()

    def is_playing(self, play_id: int) -> bool:
        """检查指定ID的音频是否正在播放"""
        channel = self.playing_sounds.get(play_id)
        if channel and channel.get_busy():
            return True
        # 如果通道已停止，从字典中移除
        if play_id in self.playing_sounds:
            self.playing_sounds.pop(play_id)
        return False

    def get_playing_count(self) -> int:
        """获取当前正在播放的音频数量"""
        # 清理已停止的音频
        stopped_ids = []
        for play_id, channel in self.playing_sounds.items():
            if not channel.get_busy():
                stopped_ids.append(play_id)

        for play_id in stopped_ids:
            self.playing_sounds.pop(play_id)

        return len(self.playing_sounds)


audio_player = AudioPlayer()
