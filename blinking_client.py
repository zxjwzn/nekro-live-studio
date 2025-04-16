#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import aiohttp
import asyncio
import time
import random
import argparse
import logging

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

async def blink_cycle(session: aiohttp.ClientSession, api_url: str, close_duration: float = 0.08, open_duration: float = 0.08, closed_hold: float = 0.05):
    """执行一次完整的眨眼周期 (异步)"""
    steps = 5 # 平滑过渡的步数

    # 1. 闭眼
    logger.debug("开始闭眼")
    for i in range(steps + 1):
        value = 1.0 - (i / steps)
        parameters = [
            {"id": "EyeOpenLeft", "value": value},
            {"id": "EyeOpenRight", "value": value}
        ]
        if not await set_parameters(session, api_url, parameters): return # 如果失败则中断
        await asyncio.sleep(close_duration / steps)

    # 2. 保持闭眼
    logger.debug("保持闭眼")
    await asyncio.sleep(closed_hold)

    # 3. 睁眼
    logger.debug("开始睁眼")
    for i in range(steps + 1):
        value = i / steps
        parameters = [
            {"id": "EyeOpenLeft", "value": value},
            {"id": "EyeOpenRight", "value": value}
        ]
        if not await set_parameters(session, api_url, parameters): return # 如果失败则中断
        await asyncio.sleep(open_duration / steps)
    
    # 确保眼睛完全睁开
    parameters = [
        {"id": "EyeOpenLeft", "value": 1.0},
        {"id": "EyeOpenRight", "value": 1.0}
    ]
    await set_parameters(session, api_url, parameters)
    logger.debug("眨眼完成")


async def main():
    parser = argparse.ArgumentParser(description='通过VTS插件API控制眨眼 (异步)')
    parser.add_argument('--api-url', type=str, default='http://localhost:8080', help='VTS插件API的URL')
    parser.add_argument('--min-interval', type=float, default=2.0, help='两次眨眼之间的最小间隔时间（秒）')
    parser.add_argument('--max-interval', type=float, default=6.0, help='两次眨眼之间的最大间隔时间（秒）')
    parser.add_argument('--close-duration', type=float, default=0.08, help='闭眼动画持续时间（秒）')
    parser.add_argument('--open-duration', type=float, default=0.08, help='睁眼动画持续时间（秒）')
    parser.add_argument('--closed-hold', type=float, default=0.05, help='眼睛闭合状态的保持时间（秒）')
    parser.add_argument('--timeout', type=float, default=5.0, help='API请求超时时间（秒）')
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
            # 尝试将眼睛设置为睁开状态
            logger.info("尝试将眼睛恢复为睁开状态...")
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