#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import signal
import random
import argparse
import math
import traceback
from typing import Optional

# 假设 vts_client 包在当前目录下或 Python 路径中
from vts_client import VTSPlugin, VTSException, APIError, ResponseError, ConnectionError, AuthenticationError

# --- 配置 ---
PLUGIN_NAME = "自动眨眼插件"
PLUGIN_DEVELOPER = "迁移自BlinkingClient"
DEFAULT_VTS_ENDPOINT = "ws://localhost:8001"

# --- 日志设置 ---
# 使用 INFO 级别，如果需要更详细的调试信息，可以在命令行参数中启用 DEBUG
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BlinkingPlugin")

# --- 全局变量 ---
plugin: Optional[VTSPlugin] = None
shutdown_event = asyncio.Event()

# --- 缓动函数 (从 easing.py 复制) ---
def ease_in_sine(t):
    """缓入正弦函数"""
    return 1 - math.cos((t * math.pi) / 2) # 使用 math.cos 实现

def ease_out_sine(t):
    """缓出正弦函数"""
    return math.sin((t * math.pi) / 2)

# --- 核心眨眼逻辑 ---
async def blink_cycle(plugin: VTSPlugin, close_duration: float = 0.08, open_duration: float = 0.08, closed_hold: float = 0.05):
    """执行一次带有缓动效果的完整眨眼周期 (异步)，结束后保持睁眼"""
    steps = 10 # 动画步数

    logger.debug("开始眨眼周期")

    # --- 眨眼动画 ---
    try:
        # 1. 闭眼 (使用 ease_out_sine 从 1.0 过渡到 0.0)
        logger.debug("开始闭眼 (缓动 1.0 -> 0.0)")
        for i in range(steps + 1):
            t = i / steps # 时间进度 (0 到 1)
            value = 1.0 * (1.0 - ease_out_sine(t)) # 值从 1.0 降到 0.0

            # 使用 plugin.set_parameter_value 设置参数
            # 注意：需要分别设置左右眼参数
            try:
                await plugin.set_parameter_value("EyeOpenLeft", value, mode="set")
                await plugin.set_parameter_value("EyeOpenRight", value, mode="set")
            except (APIError, ResponseError, ConnectionError) as e:
                logger.error(f"设置闭眼参数时出错: {e}")
                return # 出错则中断本次眨眼
            await asyncio.sleep(close_duration / steps)

        # 确保完全闭合
        try:
            await plugin.set_parameter_value("EyeOpenLeft", 0.0)
            await plugin.set_parameter_value("EyeOpenRight", 0.0)
        except (APIError, ResponseError, ConnectionError) as e:
            logger.error(f"设置完全闭眼参数时出错: {e}")
            # 即使这里出错，也继续尝试睁眼

        # 2. 保持闭眼
        logger.debug("保持闭眼")
        await asyncio.sleep(closed_hold)

        # 3. 睁眼 (使用 ease_in_sine 从 0.0 过渡到 1.0)
        logger.debug("开始睁眼 (缓动 0.0 -> 1.0)")
        for i in range(steps + 1):
            t = i / steps # 时间进度 (0 到 1)
            value = 1.0 * ease_in_sine(t) # 值从 0.0 升到 1.0

            try:
                await plugin.set_parameter_value("EyeOpenLeft", value, mode="set")
                await plugin.set_parameter_value("EyeOpenRight", value, mode="set")
            except (APIError, ResponseError, ConnectionError) as e:
                logger.error(f"设置睁眼参数时出错: {e}")
                return # 出错则中断本次眨眼
            await asyncio.sleep(open_duration / steps)

        # --- 动画结束，确保眼睛是睁开状态 (1.0) ---
        logger.debug("眨眼动画完成，确保眼睛保持睁开")
        try:
            await plugin.set_parameter_value("EyeOpenLeft", 1.0)
            await plugin.set_parameter_value("EyeOpenRight", 1.0)
            logger.debug("眼睛状态已最终设置为睁开")
        except (APIError, ResponseError, ConnectionError) as e:
            logger.error(f"设置最终睁眼状态时出错: {e}")

    except Exception as e:
        logger.error(f"执行眨眼周期时发生意外错误: {e}")
        logger.error(traceback.format_exc())


# --- 主循环 ---
async def run_blinking_loop(args):
    """运行眨眼插件的主循环"""
    global plugin
    plugin = VTSPlugin(
        plugin_name=PLUGIN_NAME,
        plugin_developer=PLUGIN_DEVELOPER,
        endpoint=args.vts_endpoint # 使用命令行参数指定的 VTS 端点
    )

    logger.info(f"尝试连接到 VTube Studio: {args.vts_endpoint}")

    try:
        # 连接与认证
        authenticated = await plugin.connect_and_authenticate()
        if not authenticated:
            logger.critical("认证失败，请检查 VTube Studio API 设置或令牌文件。")
            return

        logger.info("认证成功！开始自动眨眼循环。")
        logger.info(f"眨眼间隔: {args.min_interval:.2f}-{args.max_interval:.2f} 秒")
        logger.info(f"动画速度: 闭眼={args.close_duration:.2f}s, 睁眼={args.open_duration:.2f}s, 闭合保持={args.closed_hold:.2f}s")

        # 主循环
        while not shutdown_event.is_set():
            # 随机等待一段时间
            wait_time = random.uniform(args.min_interval, args.max_interval)
            logger.debug(f"下次眨眼等待: {wait_time:.2f} 秒")
            try:
                # 使用 asyncio.wait_for 来允许在等待期间被中断
                await asyncio.wait_for(asyncio.sleep(wait_time), timeout=wait_time + 1)
            except asyncio.TimeoutError:
                pass # 正常等待完成
            except asyncio.CancelledError:
                logger.info("等待被取消，准备退出循环...")
                break # 如果任务被取消，退出循环

            if shutdown_event.is_set():
                break # 检查是否在等待期间收到了关闭信号

            # 执行眨眼
            logger.info("执行眨眼...")
            await blink_cycle(
                plugin=plugin,
                close_duration=args.close_duration,
                open_duration=args.open_duration,
                closed_hold=args.closed_hold
            )

    except ConnectionError as e:
        logger.critical(f"无法连接到 VTube Studio: {e}")
    except AuthenticationError as e:
        logger.critical(f"认证过程中出错: {e}")
    except VTSException as e:
        logger.error(f"VTube Studio API 错误: {e}")
    except asyncio.CancelledError:
        logger.info("主任务被取消，正在关闭...")
    except Exception as e:
        logger.error(f"运行眨眼循环时发生未处理的异常: {e}")
        logger.error(traceback.format_exc())
    finally:
        # 清理操作
        logger.info("开始清理...")
        if plugin and plugin.client.is_authenticated:
            logger.info("尝试将眼睛恢复为完全睁开状态...")
            try:
                # 优先尝试设置参数，即使断开连接可能失败
                await plugin.set_parameter_value("EyeOpenLeft", 1.0)
                await plugin.set_parameter_value("EyeOpenRight", 1.0)
                logger.info("眼睛状态已尝试恢复。")
            except Exception as e_set:
                # 记录错误，但不阻塞关闭流程
                logger.warning(f"恢复眼睛状态时出错（可能已断开连接）: {e_set}")
        
        if plugin:
            await plugin.disconnect()
            logger.info("与 VTube Studio 的连接已断开。")
        
        logger.info("自动眨眼插件已关闭。")

# --- 信号处理 ---
def handle_signal(sig, frame):
    """处理 SIGINT (Ctrl+C) 和 SIGTERM"""
    logger.info(f"收到信号 {signal.Signals(sig).name}, 准备关闭...")
    # 设置事件，让主循环优雅退出
    shutdown_event.set()

# --- 入口点 ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='通过 VTSPlugin 控制模型眨眼')
    parser.add_argument('--vts-endpoint', type=str, default=DEFAULT_VTS_ENDPOINT, help=f'VTube Studio API 的 WebSocket 端点 (默认: {DEFAULT_VTS_ENDPOINT})')
    parser.add_argument('--min-interval', type=float, default=2.0, help='两次眨眼之间的最小间隔时间（秒）')
    parser.add_argument('--max-interval', type=float, default=4.0, help='两次眨眼之间的最大间隔时间（秒）')
    parser.add_argument('--close-duration', type=float, default=0.12, help='闭眼动画持续时间（秒）')
    parser.add_argument('--open-duration', type=float, default=0.24, help='睁眼动画持续时间（秒）')
    parser.add_argument('--closed-hold', type=float, default=0.03, help='眼睛闭合状态的保持时间（秒）')
    parser.add_argument('--debug', action='store_true', help='启用调试日志级别')
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
        # 可以考虑也设置 vts_client 的日志级别
        logging.getLogger("vts_client").setLevel(logging.DEBUG)

    # 设置信号处理
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    logger.info("启动自动眨眼插件...")

    # 运行主异步函数
    main_task = None
    try:
        main_task = asyncio.run(run_blinking_loop(args))
    except KeyboardInterrupt:
        logger.info("程序被 Ctrl+C 强制退出")
    except asyncio.CancelledError:
        logger.info("主事件循环被取消。")
    finally:
        if main_task and not main_task.done():
            logger.info("尝试取消主任务...")
            main_task.cancel()
            # 给予一点时间处理取消
            # asyncio.run 会自动处理任务的最终完成或取消
        logger.info("插件进程结束。") 