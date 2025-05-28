import logging

def setup_logging(debug_mode: bool = False):
    """设置日志配置"""
    log_level = logging.DEBUG if debug_mode else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if debug_mode:
        # 为特定模块设置更详细的日志级别
        logging.getLogger("vts_client").setLevel(logging.DEBUG)


# 创建全局日志记录器实例
logger = logging.getLogger("VTSModelControl")
# 可以在需要的地方通过 get_logger(__name__) 获取logger实例
# 例如: logger = get_logger(__name__)
