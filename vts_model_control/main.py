import asyncio
import logging
import signal
import sys
import json
import os
from typing import Optional

from vts_client import VTSPlugin, VTSException, ConnectionError, AuthenticationError
from utils.logger import logger, setup_logging
from config import config, VTSModelControlConfig

async def authenticate_plugin(plugin: VTSPlugin) -> bool:
    """认证VTS插件"""
    authentication_done = asyncio.Event()
    authentication_result = [False]
    
    async def auth_process():
        try:
            result = await plugin.connect_and_authenticate()
            authentication_result[0] = result
        except Exception as e:
            logger.error(f"认证过程出错: {e}", exc_info=True)
        finally:
            authentication_done.set()
    
    await asyncio.create_task(auth_process())
    
    return authentication_result[0]

async def run_main():
    plugin = VTSPlugin(
        plugin_name=config.plugin.PLUGIN_NAME,
        plugin_developer=config.plugin.PLUGIN_DEVELOPER,
        endpoint=config.plugin.DEFAULT_VTS_ENDPOINT
    )
    
    logger.info(f"尝试连接到 VTube Studio: {config.plugin.DEFAULT_VTS_ENDPOINT}")
    
    try:
        authenticated = await authenticate_plugin(plugin)
        if not authenticated:
            logger.critical("认证失败，请检查 VTube Studio API 设置或令牌文件。")
            return
        
        logger.info("认证成功！初始化动画控制器...")
        #待续

    except ConnectionError as e:
        logger.critical(f"无法连接到 VTube Studio: {e}")
    except AuthenticationError as e:
        logger.critical(f"认证过程中出错: {e}")
    except VTSException as e:
        logger.error(f"VTube Studio API 错误: {e}")
    except asyncio.CancelledError:
        logger.info("主任务被取消，正在关闭...")
    except Exception as e:
        logger.error(f"运行时发生未处理的异常: {e}", exc_info=True)

def main():
    setup_logging(config.plugin.DEBUG_MODE)
    
    logger.info(f"启动 {config.plugin.PLUGIN_NAME} 插件...")
    
    # 运行主异步函数
    try:
        asyncio.run(run_main())
    except KeyboardInterrupt:
        logger.info("程序被 Ctrl+C 强制退出")
    except Exception as e:
        logger.error(f"主程序发生错误: {e}", exc_info=True)
    finally:
        logger.info("插件进程结束。")
if __name__ == "__main__":
    main()