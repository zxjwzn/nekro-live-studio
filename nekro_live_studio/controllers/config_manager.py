import contextlib
from pathlib import Path
from typing import Optional

from ..clients.vtube_studio.plugin import plugin
from ..utils.logger import logger
from .config import ControllersConfig

CONFIG_DIR = Path("data") / "configs"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


class ConfigManager:
    """配置管理器，负责加载和保存模型特定的配置"""

    def __init__(self):
        self.current_model_name: Optional[str] = None
        self.config: ControllersConfig = ControllersConfig()

    def get_config_path(self, model_name: str) -> Path:
        """根据模型名称获取配置文件路径"""
        filename = f"{model_name}.yaml" if model_name else "default.yaml"
        return CONFIG_DIR / filename

    async def load_config_for_current_model(self) -> None:
        """加载当前 VTS 中加载的模型对应的配置"""
        try:
            with contextlib.suppress(Exception):
                model_info = await plugin.get_current_model()
                logger.info(f"model_info: {model_info}")
                if model_info and model_info.get("modelLoaded"):
                    self.current_model_name = model_info["modelName"]
                    logger.info(f"检测到模型 '{model_info['modelName']}' (ID: {model_info['modelID']})，将加载对应配置。")
                else:
                    self.current_model_name = None
                    logger.info("未检测到加载的模型，将使用默认配置。")

        except Exception as e:
            self.current_model_name = None
            logger.error(f"获取当前模型信息时出错，将使用默认配置: {e}", exc_info=True)

        model_name_to_load = self.current_model_name or "default"
        config_path = self.get_config_path(model_name_to_load)
        if config_path.exists():
            logger.info(f"正在从 {config_path} 加载配置...")
            self.config = ControllersConfig.load_config(config_path)
        else:
            logger.info(f"未找到配置文件 {config_path}，将创建并使用默认配置。")
            self.config = ControllersConfig()

        self.dump_config()

    def dump_config(self) -> None:
        """保存当前配置到文件"""
        model_name = self.current_model_name or "default"
        config_path = self.get_config_path(model_name)
        try:
            self.config.dump_config(config_path)
            logger.info(f"配置已保存到 {config_path}")
        except Exception as e:
            logger.error(f"保存配置到 {config_path} 时出错: {e}", exc_info=True)


config_manager = ConfigManager() 