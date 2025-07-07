from pathlib import Path
from typing import Dict, List

from ..schemas.audio import AudioDescriptionFile
from ..utils.logger import logger

AUDIO_DIR = Path("data/resources/audios")
DESCRIPTIONS_FILE = AUDIO_DIR / "descriptions.yaml"


class AudioManager:
    """音频管理服务"""

    def __init__(self, audio_dir: Path, descriptions_file: Path):
        self.audio_dir = audio_dir
        self.descriptions_file_path = descriptions_file
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.description_data = self._load_descriptions()

    def _load_descriptions(self) -> AudioDescriptionFile:
        """加载描述文件"""
        logger.debug(f"从 {self.descriptions_file_path} 加载音效描述...")
        return AudioDescriptionFile.load_config(self.descriptions_file_path)

    def _save_descriptions(self):
        """保存描述文件"""
        logger.debug(f"保存音效描述到 {self.descriptions_file_path}...")
        self.description_data.dump_config(self.descriptions_file_path)

    def get_sounds_with_descriptions(self) -> List[Dict[str, str]]:
        """
        获取所有音效文件及其描述。
        如果描述文件不存在或有新的音频文件，则会创建/更新描述文件。
        """
        try:
            wav_files = {p.name for p in self.audio_dir.glob("*.wav")}
        except Exception as e:
            logger.error(f"访问音频目录 {self.audio_dir} 时出错: {e}")
            return []

        existing_descriptions = self.description_data.descriptions

        # 检查是否有文件变动
        has_changes = False

        # 移除已不存在的文件的描述
        stale_files = set(existing_descriptions.keys()) - wav_files
        if stale_files:
            for file in stale_files:
                del existing_descriptions[file]
            logger.info(f"移除了 {len(stale_files)} 个不存在的音效文件的描述。")
            has_changes = True

        # 为新文件添加空的描述
        new_files_count = 0
        for file in wav_files:
            if file not in existing_descriptions:
                existing_descriptions[file] = ""
                new_files_count += 1
                has_changes = True
        
        if new_files_count > 0:
            logger.info(f"发现了 {new_files_count} 个新的音效文件, 已添加空描述。")

        # 如果有变动，则保存文件
        if has_changes:
            self.description_data.descriptions = existing_descriptions
            self._save_descriptions()

        return [{"name": name, "description": desc} for name, desc in sorted(existing_descriptions.items())]


audio_manager = AudioManager(audio_dir=AUDIO_DIR, descriptions_file=DESCRIPTIONS_FILE) 