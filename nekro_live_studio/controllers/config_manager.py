import contextlib
from pathlib import Path
from typing import Any, Dict, Optional

from ..clients.vtube_studio.plugin import plugin
from ..utils.logger import logger
from .config import ControllersConfig, ExpressionState

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

    async def sync_expressions(self):
        """同步当前模型的表情列表到配置文件"""
        if not self.current_model_name:
            return  # 没有加载模型

        if not self.config.expression_apply.ENABLED:
            logger.debug("表情同步功能已禁用。")
            return

        try:
            expressions_from_vts = await plugin.get_expressions()
            if not expressions_from_vts:
                return

            config_expressions = self.config.expression_apply.expressions
            config_expression_files = {expr.file for expr in config_expressions}

            new_expressions_added = False
            for vts_expr in expressions_from_vts:
                if vts_expr.get("file") not in config_expression_files:
                    logger.info(f"发现新表情 '{vts_expr['name']}'，已添加到配置文件中。")
                    new_expression = ExpressionState(
                        name=vts_expr["name"],
                        file=vts_expr["file"],
                        active=False,
                    )
                    config_expressions.append(new_expression)
                    new_expressions_added = True

            if new_expressions_added:
                self.dump_config()

        except Exception as e:
            logger.error(f"同步模型 '{self.current_model_name}' 的表情时出错: {e}", exc_info=True)

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

        await self.sync_expressions()
        self.dump_config()

        # 启动时应用一次表情
        from ..services.controller_manager import controller_manager
        await controller_manager.execute_oneshot("ExpressionApplyController")

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

                await self.sync_expressions()
                self.dump_config()
                logger.info(f"模型 '{model_name}' 的配置已成功加载。")

                # 应用表情并启动挂机动画
                await controller_manager.execute_oneshot("ExpressionApplyController")
                await controller_manager.start_all_idle()
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
            await controller_manager.stop_all_idle()
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