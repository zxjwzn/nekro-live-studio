import asyncio
import logging
import signal
import sys
import json
import os
from typing import Optional

from vts_client import VTSPlugin, VTSException, ConnectionError, AuthenticationError
from config import config, VTSModelControlConfig
from utils.logger import logger, setup_logging

# 全局变量
shutdown_event = asyncio.Event()

def handle_signal(sig, frame):
    """处理信号"""
    logger.info(f"收到信号 {signal.Signals(sig).name}, 准备关闭...")
    shutdown_event.set()

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
    
    auth_task = asyncio.create_task(auth_process())
    
    # 等待认证完成或收到关闭信号
    while not authentication_done.is_set() and not shutdown_event.is_set():
        try:
            await asyncio.wait_for(
                asyncio.gather(
                    authentication_done.wait(),
                    shutdown_event.wait()
                ),
                timeout=0.1
            )
        except asyncio.TimeoutError:
            pass
    
    # 如果收到关闭信号且认证未完成，取消认证任务
    if shutdown_event.is_set() and not authentication_done.is_set():
        logger.info("在认证过程中收到关闭信号，中止连接...")
        auth_task.cancel()
        try:
            await auth_task
        except asyncio.CancelledError:
            pass
        return False
    
    return authentication_result[0]

async def run_controller(config: VTSModelControlConfig):
    """运行控制器主函数"""
    plugin = VTSPlugin(
        plugin_name=config.plugin.PLUGIN_NAME,
        plugin_developer=config.plugin.PLUGIN_DEVELOPER,
        endpoint=config.plugin.DEFAULT_VTS_ENDPOINT
    )
    
    logger.info(f"尝试连接到 VTube Studio: {config.plugin.DEFAULT_VTS_ENDPOINT}")
    
    try:
        # 认证
        authenticated = await authenticate_plugin(plugin)
        if not authenticated:
            logger.critical("认证失败，请检查 VTube Studio API 设置或令牌文件。")
            return
        
        logger.info("认证成功！初始化动画控制器...")
        
        # 创建动画管理器
        manager = AnimationManager(plugin, config, logger)
        manager.initialize()
        
        # 存储初始参数值
        await manager.store_initial_parameters()
        
        # 启动所有动画
        await manager.start_all()
        
        # 等待关闭信号
        while not shutdown_event.is_set():
            await asyncio.sleep(0.5)
            
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
    finally:
        # 清理操作
        logger.info("开始清理...")
        
        if 'manager' in locals():
            # 停止所有动画
            await manager.stop_all()
            
            # 恢复参数
            await manager.restore_parameters()
        
        if plugin and plugin.client.is_authenticated:
            await plugin.disconnect()
            logger.info("与 VTube Studio 的连接已断开。")
        
        logger.info("插件已关闭。")

def main():
    """主函数"""
    
    # 设置日志
    setup_logging(config.plugin.DEBUG_MODE)
    
    # 设置信号处理
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    logger.info(f"启动 {config.plugin.PLUGIN_NAME} 插件...")
    
    # 运行主异步函数
    try:
        asyncio.run(run_controller(config))
    except KeyboardInterrupt:
        logger.info("程序被 Ctrl+C 强制退出")
    except Exception as e:
        logger.error(f"主程序发生错误: {e}", exc_info=True)
    finally:
        logger.info("插件进程结束。")

if __name__ == "__main__":
    main()