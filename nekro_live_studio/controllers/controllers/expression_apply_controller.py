from ...clients.vtube_studio.plugin import plugin
from ...utils.logger import logger
from ..base_controller import OneShotController
from ..config import ExpressionApplyConfig
from ..config_manager import config_manager


class ExpressionApplyController(OneShotController[ExpressionApplyConfig]):
    """
    根据配置应用表情状态
    """

    @property
    def config(self) -> ExpressionApplyConfig:
        return config_manager.config.expression_apply

    async def execute(self, *args, **kwargs):
        if not self.config.ENABLED:
            logger.info("表情应用功能已禁用，跳过执行。")
            return
        
        if not self.config.expressions:
            logger.info("配置中没有表情，跳过表情应用。")
            return

        logger.info("正在根据配置应用表情...")
        for expression_state in self.config.expressions:
            try:
                await plugin.activate_expression(
                    expression_file=expression_state.file, active=expression_state.active
                )
                if expression_state.active:
                    logger.info(f"已激活表情: '{expression_state.name}'")
            except Exception as e:
                logger.error(
                    f"应用表情 '{expression_state.name}' 状态时出错: {e}", exc_info=True
                )
        logger.info("表情应用完成。") 