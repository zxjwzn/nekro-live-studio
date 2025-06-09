import io
import os
from pathlib import Path
from typing import Dict, Optional

import pygame
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