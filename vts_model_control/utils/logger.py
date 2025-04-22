import logging

# 全局日志对象
logger = logging.getLogger("VTSModelControl")

def setup_logging(debug_mode: bool = False):
    """设置日志"""
    log_level = logging.DEBUG if debug_mode else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger.setLevel(log_level)
    if debug_mode:
        logging.getLogger("vts_client").setLevel(logging.DEBUG)
