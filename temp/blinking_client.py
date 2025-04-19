#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import aiohttp
import asyncio
import time
import random
import argparse
import logging
# 导入缓动函数
from easing import ease_in_sine, ease_out_sine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('BlinkingClient')

async def set_parameters(session: aiohttp.ClientSession, api_url: str, parameters: list):
    """调用插件API设置多个参数 (异步)"""
    endpoint = f"{api_url}/parameters"
    try:
        async with session.post(endpoint, json={"parameters": parameters}) as response:
            response.raise_for_status() # 如果请求失败则抛出异常 (4xx, 5xx)
            result = await response.json()
            if not result.get("success", False):
                logger.error(f"设置参数失败: {result.get('error', '未知错误')}")
                return False
            logger.debug(f"成功设置参数: {parameters}")
            return True
    except aiohttp.ClientResponseError as e:
        logger.error(f"调用API时出错 ({endpoint}): HTTP {e.status} - {e.message}")
        return False
    except aiohttp.ClientConnectionError as e:
        logger.error(f"无法连接到API ({endpoint}): {e}")
        return False
    except asyncio.TimeoutError:
        logger.error(f"调用API超时 ({endpoint})")
        return False
    except Exception as e:
        logger.error(f"设置参数时发生未知错误: {e}")
        return False

async def get_parameter_values(session: aiohttp.ClientSession, api_url: str, parameter_ids: list[str]) -> dict[str, float]:
    """从插件API获取指定参数的当前值 (异步)"""
    endpoint = f"{api_url}/parameters"
    values = {param_id: 1.0 for param_id in parameter_ids} # 默认值设为1.0 (睁眼)

    try:
        async with session.get(endpoint) as response:
            response.raise_for_status()
            result = await response.json()
            if 'parameters' in result:
                param_map = {p.get('name'): p.get('value', 1.0) for p in result['parameters']}
                for param_id in parameter_ids:
                    if param_id in param_map:
                        values[param_id] = param_map[param_id]
                    else:
                         logger.warning(f"在API响应中未找到参数 '{param_id}'，使用默认值 1.0")
                logger.debug(f"成功获取参数值: {values}")
            else:
                logger.warning(f"获取参数响应格式不正确，使用默认值: {result}")
            return values
    except aiohttp.ClientResponseError as e:
        logger.error(f"调用API获取参数时出错 ({endpoint}): HTTP {e.status} - {e.message}")
        return values
    except aiohttp.ClientConnectionError as e:
        logger.error(f"无法连接到API获取参数 ({endpoint}): {e}")
        return values
    except asyncio.TimeoutError:
        logger.error(f"调用API获取参数超时 ({endpoint})")
        return values
    except Exception as e:
        logger.error(f"获取参数值时发生未知错误: {e}")
        return values

async def blink_cycle(session: aiohttp.ClientSession, api_url: str, close_duration: float = 0.08, open_duration: float = 0.08, closed_hold: float = 0.05):
    """执行一次带有缓动效果的完整眨眼周期 (异步)，结束后保持睁眼"""
    steps = 10 # 增加步数以获得更平滑的缓动效果

    # 获取当前眼睛状态 (仅用于日志记录)
    logger.debug("获取当前眼睛参数值...")
    current_eye_values = await get_parameter_values(session, api_url, ["EyeOpenLeft", "EyeOpenRight"])
    start_left = current_eye_values.get("EyeOpenLeft", 1.0)
    start_right = current_eye_values.get("EyeOpenRight", 1.0)
    logger.debug(f"当前眼睛状态: Left={start_left:.2f}, Right={start_right:.2f}")

    # --- 眨眼动画（始终基于 1.0 -> 0.0 -> 1.0 的范围） ---

    # 1. 闭眼 (使用 ease_in_sine 从 1.0 过渡到 0.0)
    logger.debug("开始闭眼 (缓动 1.0 -> 0.0)")
    for i in range(steps + 1):
        t = i / steps # 时间进度 (0 到 1)
        # ease_in_sine(t) 从 0 增加到 1
        # (1 - ease_in_sine(t)) 从 1 减少到 0
        value = 1.0 * (1.0 - ease_out_sine(t))

        parameters = [
            {"id": "EyeOpenLeft", "value": value},
            {"id": "EyeOpenRight", "value": value}
        ]
        if not await set_parameters(session, api_url, parameters): return
        await asyncio.sleep(close_duration / steps)

    # 确保完全闭合
    parameters = [
        {"id": "EyeOpenLeft", "value": 0.0},
        {"id": "EyeOpenRight", "value": 0.0},
    ]
    await set_parameters(session, api_url, parameters)

    # 2. 保持闭眼
    logger.debug("保持闭眼")
    await asyncio.sleep(closed_hold)

    # 3. 睁眼 (使用 ease_out_sine 从 0 过渡回初始值)
    logger.debug("开始睁眼 (缓动 0.0 -> 1.0)")
    for i in range(steps + 1):
        t = i / steps # 时间进度 (0 到 1)
        # ease_out_sine(t) 从 0 增加到 1
        value = 1.0 * ease_in_sine(t)

        parameters = [
            {"id": "EyeOpenLeft", "value": value},
            {"id": "EyeOpenRight", "value": value}
        ]
        if not await set_parameters(session, api_url, parameters): return
        await asyncio.sleep(open_duration / steps)

    # --- 动画结束，确保眼睛是睁开状态 (1.0) ---
    logger.debug(f"眨眼动画完成，确保眼睛保持睁开")
    parameters = [
        {"id": "EyeOpenLeft", "value": 1.0}, # 强制设为 1.0
        {"id": "EyeOpenRight", "value": 1.0} # 强制设为 1.0
    ]
    await set_parameters(session, api_url, parameters)
    logger.debug("眼睛状态已设置为睁开")

async def main():
    parser = argparse.ArgumentParser(description='通过VTS插件API控制眨眼 (异步)')
    parser.add_argument('--api-url', type=str, default='http://localhost:8080', help='VTS插件API的URL')
    parser.add_argument('--min-interval', type=float, default=2.0, help='两次眨眼之间的最小间隔时间（秒）')
    parser.add_argument('--max-interval', type=float, default=4.0, help='两次眨眼之间的最大间隔时间（秒）')
    parser.add_argument('--close-duration', type=float, default=0.12, help='闭眼动画持续时间（秒）')
    parser.add_argument('--open-duration', type=float, default=0.24, help='睁眼动画持续时间（秒）')
    parser.add_argument('--closed-hold', type=float, default=0.03, help='眼睛闭合状态的保持时间（秒）')
    parser.add_argument('--timeout', type=float, default=1.0, help='API请求超时时间（秒）')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    logger.info(f"启动异步眨眼客户端，连接到: {args.api_url}")
    logger.info(f"眨眼间隔: {args.min_interval}-{args.max_interval}秒")
    logger.info(f"动画速度: 闭眼={args.close_duration}s, 睁眼={args.open_duration}s, 闭合保持={args.closed_hold}s")

    # 创建aiohttp客户端会话
    timeout = aiohttp.ClientTimeout(total=args.timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            while True:
                # 随机等待一段时间
                wait_time = random.uniform(args.min_interval, args.max_interval)
                logger.debug(f"下次眨眼等待: {wait_time:.2f} 秒")
                await asyncio.sleep(wait_time)

                # 执行眨眼
                logger.info("执行眨眼...")
                await blink_cycle(
                    session=session,
                    api_url=args.api_url,
                    close_duration=args.close_duration,
                    open_duration=args.open_duration,
                    closed_hold=args.closed_hold
                )

        except KeyboardInterrupt:
            logger.info("接收到中断信号，正在关闭...")
        except asyncio.CancelledError:
             logger.info("任务被取消，正在关闭...")
        except Exception as e:
            logger.error(f"发生未处理的异常: {e}")
        finally:
            # 尝试将眼睛设置为睁开状态 (恢复到 1.0)
            logger.info("尝试将眼睛恢复为完全睁开状态...")
            await set_parameters(session, args.api_url, [
                {"id": "EyeOpenLeft", "value": 1.0},
                {"id": "EyeOpenRight", "value": 1.0}
            ])
            logger.info("异步眨眼客户端已关闭。")

if __name__ == "__main__":
    # 运行异步主函数
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序被强制退出") 