#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VTube Studio 动画控制测试脚本
用于测试动画控制功能
"""

import asyncio
import json
import logging
import aiohttp
import argparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('VTS_Animation_Test')

class VTSAnimationTester:
    """VTube Studio 动画控制测试类"""
    
    def __init__(self, api_url='http://localhost:8080'):
        """初始化测试器
        
        Args:
            api_url: 插件API URL
        """
        self.api_url = api_url
        self.session = None
    
    async def initialize(self):
        """初始化测试器"""
        self.session = aiohttp.ClientSession()
        logger.info(f"已连接到API: {self.api_url}")
    
    async def close(self):
        """关闭测试器"""
        if self.session:
            await self.session.close()
            logger.info("已关闭会话")
    
    async def get_status(self):
        """获取插件状态"""
        logger.info("获取插件状态...")
        async with self.session.get(f"{self.api_url}/status") as response:
            if response.status == 200:
                data = await response.json()
                logger.info(f"插件状态: {json.dumps(data, ensure_ascii=False)}")
                return data
            else:
                logger.error(f"获取状态失败: {response.status}")
                return None
    
    async def get_items(self):
        """获取场景中的物品列表"""
        logger.info("获取场景物品列表...")
        async with self.session.get(f"{self.api_url}/items") as response:
            if response.status == 200:
                data = await response.json()
                items = data.get('items', [])
                logger.info(f"获取到 {len(items)} 个场景物品")
                
                # 打印物品信息
                for i, item in enumerate(items):
                    item_id = item.get('instanceID', 'unknown')
                    item_name = item.get('fileName', 'unknown')
                    is_animated = item.get('isAnimated', False)
                    logger.info(f"物品 {i+1}: ID={item_id}, 名称={item_name}, 是否动画={is_animated}")
                
                return data
            else:
                logger.error(f"获取物品列表失败: {response.status}")
                return None
    
    async def play_animation(self, item_id, frame_rate=30):
        """播放动画
        
        Args:
            item_id: 物品实例ID
            frame_rate: 帧率
            
        Returns:
            是否成功
        """
        logger.info(f"播放动画: 物品ID={item_id}, 帧率={frame_rate}")
        data = {
            "itemInstanceID": item_id,
            "frameRate": frame_rate
        }
        
        async with self.session.post(f"{self.api_url}/animation/play", json=data) as response:
            if response.status == 200:
                result = await response.json()
                success = result.get('success', False)
                logger.info(f"播放动画结果: {'成功' if success else '失败'}")
                return success
            else:
                logger.error(f"播放动画请求失败: {response.status}")
                return False
    
    async def stop_animation(self, item_id):
        """停止动画
        
        Args:
            item_id: 物品实例ID
            
        Returns:
            是否成功
        """
        logger.info(f"停止动画: 物品ID={item_id}")
        data = {
            "itemInstanceID": item_id
        }
        
        async with self.session.post(f"{self.api_url}/animation/stop", json=data) as response:
            if response.status == 200:
                result = await response.json()
                success = result.get('success', False)
                logger.info(f"停止动画结果: {'成功' if success else '失败'}")
                return success
            else:
                logger.error(f"停止动画请求失败: {response.status}")
                return False
    
    async def control_animation(self, item_id, play_animation=None, frame_rate=None, frame=None, auto_stop_frames=None):
        """控制动画
        
        Args:
            item_id: 物品实例ID
            play_animation: 是否播放动画
            frame_rate: 帧率
            frame: 跳转到指定帧
            auto_stop_frames: 自动停止帧列表
            
        Returns:
            是否成功
        """
        logger.info(f"控制动画: 物品ID={item_id}")
        data = {
            "itemInstanceID": item_id
        }
        
        if play_animation is not None:
            data["playAnimation"] = play_animation
            
        if frame_rate is not None:
            data["frameRate"] = frame_rate
            
        if frame is not None:
            data["frame"] = frame
            
        if auto_stop_frames is not None:
            data["autoStopFrames"] = auto_stop_frames
        
        async with self.session.post(f"{self.api_url}/animation/control", json=data) as response:
            if response.status == 200:
                result = await response.json()
                success = result.get('success', False)
                logger.info(f"控制动画结果: {'成功' if success else '失败'}")
                return success
            else:
                logger.error(f"控制动画请求失败: {response.status}")
                return False
    
    async def run_tests(self):
        """运行测试"""
        try:
            # 获取插件状态
            status = await self.get_status()
            if not status:
                logger.error("获取状态失败，终止测试")
                return False
            
            # 获取场景物品列表
            items_data = await self.get_items()
            if not items_data:
                logger.error("获取物品列表失败，终止测试")
                return False
            
            items = items_data.get('items', [])
            if not items:
                logger.warning("场景中没有物品，无法测试动画控制功能")
                return False
            
            # 找到第一个动画物品
            animated_item = None
            for item in items:
                if item.get('isAnimated', False):
                    animated_item = item
                    break
            
            if not animated_item:
                logger.warning("场景中没有动画物品，无法测试动画控制功能")
                return False
            
            item_id = animated_item.get('instanceID')
            item_name = animated_item.get('fileName')
            logger.info(f"找到动画物品: ID={item_id}, 名称={item_name}")
            
            # 测试播放动画
            logger.info("测试播放动画...")
            play_success = await self.play_animation(item_id, 30)
            if not play_success:
                logger.error("播放动画失败")
            else:
                logger.info("播放动画成功，等待3秒...")
                await asyncio.sleep(3)
            
            # 测试停止动画
            logger.info("测试停止动画...")
            stop_success = await self.stop_animation(item_id)
            if not stop_success:
                logger.error("停止动画失败")
            else:
                logger.info("停止动画成功，等待1秒...")
                await asyncio.sleep(1)
            
            # 测试控制动画 - 设置帧率并播放
            logger.info("测试控制动画 - 设置帧率并播放...")
            control_success1 = await self.control_animation(item_id, play_animation=True, frame_rate=15)
            if not control_success1:
                logger.error("控制动画失败")
            else:
                logger.info("控制动画成功，等待3秒...")
                await asyncio.sleep(3)
            
            # 测试控制动画 - 跳转到特定帧
            logger.info("测试控制动画 - 跳转到特定帧...")
            control_success2 = await self.control_animation(item_id, frame=5)
            if not control_success2:
                logger.error("控制动画失败")
            else:
                logger.info("控制动画成功，等待1秒...")
                await asyncio.sleep(1)
            
            # 测试控制动画 - 设置自动停止帧
            logger.info("测试控制动画 - 设置自动停止帧...")
            control_success3 = await self.control_animation(item_id, play_animation=True, auto_stop_frames=[10])
            if not control_success3:
                logger.error("控制动画失败")
            else:
                logger.info("控制动画成功，等待5秒...")
                await asyncio.sleep(5)
            
            logger.info("测试完成")
            return True
        except Exception as e:
            logger.error(f"测试过程中出错: {e}", exc_info=True)
            return False

async def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='VTube Studio 动画控制测试')
    parser.add_argument('--api-url', type=str, default='http://localhost:8080', help='插件API URL')
    args = parser.parse_args()
    
    # 创建测试器
    tester = VTSAnimationTester(api_url=args.api_url)
    
    try:
        # 初始化测试器
        await tester.initialize()
        
        # 运行测试
        await tester.run_tests()
    except KeyboardInterrupt:
        logger.info("接收到中断信号，正在关闭...")
    finally:
        # 关闭测试器
        await tester.close()

if __name__ == "__main__":
    asyncio.run(main())
