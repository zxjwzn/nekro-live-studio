import logging

def setup_logging(debug_mode: bool = False):
    """设置日志"""
    log_level = logging.DEBUG if debug_mode else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # logger.setLevel(log_level) # 不再需要设置全局logger的level
    if debug_mode:
        # 如果需要，可以为特定logger设置更详细的级别，例如 vts_client
        logging.getLogger("vts_client").setLevel(logging.DEBUG)
        # get_logger("VTSModelControl").info("调试模式已启用，日志级别设置为DEBUG")
    else:
        # get_logger("VTSModelControl").info("日志级别设置为INFO")
        pass


logger = logging.getLogger("VTSModelControl")
# 可以在需要的地方通过 get_logger(__name__) 获取logger实例
# 例如: logger = get_logger(__name__)
