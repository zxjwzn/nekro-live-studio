import contextlib
from pathlib import Path
from typing import Any, Dict, Optional

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

    async def on_model_loaded_event(self, event_data: Dict[str, Any]) -> None:
        """处理模型加载/卸载事件"""
        event_data = event_data.get("data",{})
        model_loaded = event_data.get("modelLoaded", False)
        model_name = event_data.get("modelName")
        model_id = event_data.get("modelID")
        # 导入 controller_manager 以重新启动控制器
        from ..services.controller_manager import controller_manager
        
        if model_loaded:
            # 模型加载
            if model_name:
                logger.info(f"检测到模型切换事件：'{model_name}' (ID: {model_id}) 已加载，正在加载对应配置...")
                self.current_model_name = model_name
                config_path = self.get_config_path(model_name)
                
                if config_path.exists():
                    logger.info(f"正在从 {config_path} 加载配置...")
                    self.config = ControllersConfig.load_config(config_path)
                else:
                    logger.info(f"未找到配置文件 {config_path}，将创建并使用默认配置。")
                    self.config = ControllersConfig()
                
                self.dump_config()
                logger.info(f"模型 '{model_name}' 的配置已成功加载。")
                
            else:
                logger.warning("收到模型加载事件，但未包含模型名称信息。")
        else:
            # 模型卸载
            if model_name:
                logger.info(f"检测到模型卸载事件：'{model_name}' (ID: {model_id}) 已卸载，切换到默认配置...")
            else:
                logger.info("检测到模型卸载事件，切换到默认配置...")
            
            self.current_model_name = None
            config_path = self.get_config_path("default")
            
            if config_path.exists():
                logger.info(f"正在从 {config_path} 加载默认配置...")
                self.config = ControllersConfig.load_config(config_path)
            else:
                logger.info(f"未找到默认配置文件 {config_path}，将创建并使用默认配置。")
                self.config = ControllersConfig()
            
            self.dump_config()
            logger.info("已切换到默认配置。")

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