#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import signal
import random
import math
import traceback
from typing import Optional

# 假设 vts_client 包在当前目录下或 Python 路径中
from vts_client import VTSPlugin, VTSException, APIError, ResponseError, ConnectionError, AuthenticationError
from easing import ease_out_sine, ease_in_sine

# --- 配置 ---
PLUGIN_NAME = "自动眨眼插件"
PLUGIN_DEVELOPER = "迁移自BlinkingClient"
DEFAULT_VTS_ENDPOINT = "ws://localhost:8001"

# --- 眨眼配置 ---
MIN_INTERVAL = 2.0  # 两次眨眼之间的最小间隔时间（秒）
MAX_INTERVAL = 4.0  # 两次眨眼之间的最大间隔时间（秒）
CLOSE_DURATION = 0.12  # 闭眼动画持续时间（秒）
OPEN_DURATION = 0.24  # 睁眼动画持续时间（秒）
CLOSED_HOLD = 0.03  # 眼睛闭合状态的保持时间（秒）
DEBUG_MODE = False  # 是否启用调试模式

# --- 日志设置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BlinkingPlugin")
if DEBUG_MODE:
    logger.setLevel(logging.DEBUG)
    logging.getLogger("vts_client").setLevel(logging.DEBUG)

# --- 全局变量 ---
plugin: Optional[VTSPlugin] = None
shutdown_event = asyncio.Event()

# --- 核心眨眼逻辑 ---
async def blink_cycle(plugin: VTSPlugin, close_duration: float = 0.08, open_duration: float = 0.08, closed_hold: float = 0.05):
    """执行一次带有缓动效果的完整眨眼周期 (异步)，结束后保持睁眼"""
    steps = 10 # 动画步数

    logger.debug("开始眨眼周期")

    # --- 眨眼动画 ---
    try:
        # 1. 闭眼 (使用 ease_out_sine 从 1.0 过渡到 0.0)
        logger.debug("开始闭眼 (缓动 1.0 -> 0.0)")
        start_time = asyncio.get_event_loop().time()
        end_time = start_time + close_duration
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time >= end_time:
                break
                
            # 计算进度比例
            elapsed = current_time - start_time
            progress = min(1.0, elapsed / close_duration)
            value = 1.0 * (1.0 - ease_in_sine(progress)) # 值从 1.0 降到 0.0

            # 使用 plugin.set_parameter_value 设置参数
            try:
                await plugin.set_parameter_value("EyeOpenLeft", value, mode="set")
                await plugin.set_parameter_value("EyeOpenRight", value, mode="set")
            except (APIError, ResponseError, ConnectionError) as e:
                logger.error(f"设置闭眼参数时出错: {e}")
                return # 出错则中断本次眨眼
                
            # 计算需要等待的时间，保证动画平滑但不超过总时长
            next_step_time = min(current_time + 0.016, end_time)  # 约60fps，最多等待16ms
            sleep_time = max(0, next_step_time - asyncio.get_event_loop().time())
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

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
        start_time = asyncio.get_event_loop().time()
        end_time = start_time + open_duration
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time >= end_time:
                break
                
            # 计算进度比例
            elapsed = current_time - start_time
            progress = min(1.0, elapsed / open_duration)
            value = 1.0 * ease_in_sine(progress) # 值从 0.0 升到 1.0

            try:
                await plugin.set_parameter_value("EyeOpenLeft", value, mode="set")
                await plugin.set_parameter_value("EyeOpenRight", value, mode="set")
            except (APIError, ResponseError, ConnectionError) as e:
                logger.error(f"设置睁眼参数时出错: {e}")
                return # 出错则中断本次眨眼
                
            # 计算需要等待的时间，保证动画平滑但不超过总时长
            next_step_time = min(current_time + 0.016, end_time)  # 约60fps，最多等待16ms
            sleep_time = max(0, next_step_time - asyncio.get_event_loop().time())
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

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
async def run_blinking_loop():
    """运行眨眼插件的主循环"""
    global plugin
    plugin = VTSPlugin(
        plugin_name=PLUGIN_NAME,
        plugin_developer=PLUGIN_DEVELOPER,
        endpoint=DEFAULT_VTS_ENDPOINT
    )

    logger.info(f"尝试连接到 VTube Studio: {DEFAULT_VTS_ENDPOINT}")

    try:
        # 连接与认证
        authenticated = await plugin.connect_and_authenticate()
        if not authenticated:
            logger.critical("认证失败，请检查 VTube Studio API 设置或令牌文件。")
            return

        logger.info("认证成功！开始自动眨眼循环。")
        logger.info(f"眨眼间隔: {MIN_INTERVAL:.2f}-{MAX_INTERVAL:.2f} 秒")
        logger.info(f"动画速度: 闭眼={CLOSE_DURATION:.2f}s, 睁眼={OPEN_DURATION:.2f}s, 闭合保持={CLOSED_HOLD:.2f}s")

        # 主循环
        while not shutdown_event.is_set():
            # 随机等待一段时间
            wait_time = random.uniform(MIN_INTERVAL, MAX_INTERVAL)
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
                close_duration=CLOSE_DURATION,
                open_duration=OPEN_DURATION,
                closed_hold=CLOSED_HOLD
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
    # 设置信号处理
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    logger.info("启动自动眨眼插件...")

    # 运行主异步函数
    main_task = None
    try:
        main_task = asyncio.run(run_blinking_loop())
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