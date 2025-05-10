import asyncio
import pygame
from typing import List, Optional
from utils.logger import logger
class AudioPlayer:

    def __init__(self, audio_file_path: str, text_rate: float, volume: float):
        try:
            pygame.mixer.init()
            self.sound = pygame.mixer.Sound(audio_file_path)
            self.volume = max(0.0, min(1.0, volume)) # 确保音量在0.0-1.0之间
            self.sound.set_volume(self.volume)
            logger.info(f"音频文件 {audio_file_path} 加载成功。音量设置为: {self.volume:.2f}")
        except pygame.error as e:
            logger.error(f"加载音频文件 {audio_file_path} 失败: {e}")
            self.sound = None
        except Exception as e:
            logger.error(f"pygame.mixer 初始化失败: {e}. 音频播放功能将不可用。")
            self.sound = None
        
        self.default_text_rate = text_rate # 存储配置中的默认速率
        # self.char_interval 将在 play_text_as_speech 中根据具体速率动态计算

    async def play_text_as_speech(self, text_segments: List[str], speeds: Optional[List[float]] = None):
        if not self.sound:
            logger.warning("音频播放器未正确初始化或音频文件加载失败，无法播放语音。")
            return

        if not text_segments: # 如果文本列表为空
            logger.debug("接收到空的文本列表，无需播放。")
            return

        for i, segment in enumerate(text_segments):
            num_chars = len(segment)
            if num_chars == 0:
                logger.debug(f"文本片段 {i+1} 为空，跳过。")
                continue

            current_speed = self.default_text_rate
            if speeds and i < len(speeds) and speeds[i] > 0:
                current_speed = speeds[i]
                logger.debug(f"文本片段 {i+1} 使用自定义速率: {current_speed:.2f} 字/秒")
            else:
                logger.debug(f"文本片段 {i+1} 使用默认速率: {current_speed:.2f} 字/秒 (原因: speeds列表未提供，或索引越界，或速度值无效)")
            
            char_interval = 1.0 / current_speed if current_speed > 0 else float('inf')

            logger.info(f"准备播放文本片段 {i+1}/{len(text_segments)}: '{segment[:20]}...' ({num_chars}字), 速率: {current_speed:.2f} 字/秒, 音量: {self.volume:.2f}")

            for char_index in range(num_chars):
                try:
                    self.sound.play()
                except pygame.error as e:
                    logger.error(f"播放音效时出错 (片段 {i+1}, 字符 {char_index+1}): {e}")
                
                if char_index < num_chars - 1:  # 最后一个字后面不需要暂停
                    if char_interval != float('inf'):
                        try:
                            await asyncio.sleep(char_interval)
                        except asyncio.CancelledError:
                            logger.info(f"语音播放任务 (片段 {i+1}) 被取消。")
                            # 如果一个片段被取消，我们可能希望停止整个多片段播放
                            # 或者根据需求继续播放下一个片段。这里选择抛出让上层处理。
                            raise 
            logger.info(f"文本片段 {i+1} '{segment[:20]}...' 播放完成。")
            if i < len(text_segments) - 1: # 如果这不是最后一个文本片段
                try:
                    await asyncio.sleep(1) # 在片段之间添加0.15秒的停顿
                except asyncio.CancelledError:
                    logger.info("语音播放任务在片段间等待时被取消。")
                    raise
            logger.info(f"[AudioPlayer Debug] Processing segment index: {i}, Received speeds list: {speeds}, Default rate: {self.default_text_rate}")
        logger.info("所有文本片段播放完成。")
        

    def stop_all_sounds(self):
        if pygame.mixer.get_init(): # 检查mixer是否已初始化
            pygame.mixer.stop()
            logger.info("所有音效已停止。") 