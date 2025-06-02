import asyncio
import pygame
from typing import List, Optional
from utils.logger import logger


class AudioManager:
    def __init__(
        self, rpg_sound_file_path: str, default_text_rate: float, default_volume: float
    ):
        try:
            pygame.mixer.init()
            self.rpg_sound = pygame.mixer.Sound(rpg_sound_file_path)
            self.default_volume = max(
                0.0, min(1.0, default_volume)
            )  # 确保音量在0.0-1.0之间
            self.rpg_sound.set_volume(self.default_volume)
            logger.info(
                f"RPG音效文件 {rpg_sound_file_path} 加载成功。默认音量设置为: {self.default_volume:.2f}"
            )
        except pygame.error as e:
            logger.error(f"加载RPG音效文件 {rpg_sound_file_path} 失败: {e}")
            self.rpg_sound = None
        except Exception as e:
            logger.error(
                f"pygame.mixer 初始化或RPG音效加载失败: {e}. 部分音频功能可能不可用。"
            )
            self.rpg_sound = None

        self.default_text_rate = default_text_rate

    async def play_text_as_speech(
        self, text_segments: List[str], speeds: Optional[List[float]] = None
    ):
        if not self.rpg_sound:
            logger.warning("RPG音效未正确初始化或加载失败，无法播放RPG风格语音。")
            return

        if not text_segments:  # 如果文本列表为空
            logger.debug("接收到空的文本列表，无需播放RPG语音。")
            return

        for i, segment in enumerate(text_segments):
            num_chars = len(segment)
            if num_chars == 0:
                logger.debug(f"RPG语音文本片段 {i + 1} 为空，跳过。")
                continue

            current_speed = self.default_text_rate
            if speeds and i < len(speeds) and speeds[i] > 0:
                current_speed = speeds[i]
                logger.debug(
                    f"RPG语音文本片段 {i + 1} 使用自定义速率: {current_speed:.2f} 字/秒"
                )
            else:
                logger.debug(
                    f"RPG语音文本片段 {i + 1} 使用默认速率: {current_speed:.2f} 字/秒 (原因: speeds列表未提供，或索引越界，或速度值无效)"
                )

            char_interval = 1.0 / current_speed if current_speed > 0 else float("inf")

            logger.info(
                f"准备播放RPG语音文本片段 {i + 1}/{len(text_segments)}: '{segment[:20]}...' ({num_chars}字), 速率: {current_speed:.2f} 字/秒, 音量: {self.rpg_sound.get_volume():.2f}"
            )

            for char_index in range(num_chars):
                try:
                    self.rpg_sound.play()
                except pygame.error as e:
                    logger.error(
                        f"播放RPG音效时出错 (片段 {i + 1}, 字符 {char_index + 1}): {e}"
                    )

                if char_index < num_chars - 1:  # 最后一个字后面不需要暂停
                    if char_interval != float("inf"):
                        try:
                            await asyncio.sleep(char_interval)
                        except asyncio.CancelledError:
                            logger.info(f"RPG语音播放任务 (片段 {i + 1}) 被取消。")
                            raise
            logger.info(f"RPG语音文本片段 {i + 1} '{segment[:20]}...' 播放完成。")
        logger.info("所有RPG语音文本片段播放完成。")

    async def play_sound(
        self, audio_file_path: str, volume: Optional[float] = None, loops: int = 0
    ):
        """
        播放指定路径的音频文件。

        Args:
            audio_file_path (str): 要播放的音频文件的路径。
            volume (Optional[float]): 播放音量 (0.0 到 1.0)。如果为 None，则使用AudioManager的默认音量。
            loops (int): 音频循环播放的次数。0 表示播放一次，-1 表示无限循环。
        """
        if not pygame.mixer.get_init():
            logger.error("pygame.mixer 未初始化，无法播放音频。")
            return

        try:
            sound_to_play = pygame.mixer.Sound(audio_file_path)
            play_volume = self.default_volume
            if volume is not None:
                play_volume = max(0.0, min(1.0, volume))

            sound_to_play.set_volume(play_volume)
            sound_to_play.play(loops=loops)
            logger.info(
                f"开始播放音频: {audio_file_path}, 音量: {play_volume:.2f}, 循环次数: {loops}"
            )

        except pygame.error as e:
            logger.error(f"加载或播放音频文件 {audio_file_path} 失败: {e}")
        except Exception as e:
            logger.error(f"播放音频 {audio_file_path} 时发生未知错误: {e}")

    def stop_all_sounds(self):
        if pygame.mixer.get_init():  # 检查mixer是否已初始化
            pygame.mixer.stop()
            logger.info("所有通过 AudioManager 播放的音效已尝试停止。")
