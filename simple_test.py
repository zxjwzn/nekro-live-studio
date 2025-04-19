"""
简单测试脚本，用于测试VTubeStudio插件的认证流程
"""

import asyncio
import logging
import sys

from vts_client import VTSPlugin

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

async def main():
    # 创建插件实例
    plugin = VTSPlugin(
        plugin_name="测试插件",
        plugin_developer="测试开发者",
        endpoint="ws://localhost:8001"  # 使用提供的远程地址
    )
    
    try:
        # 连接并认证
        print("正在连接并认证...")
        success = await plugin.connect_and_authenticate()
        
        if success:
            print("认证成功！")
            
            # 获取当前模型信息
            print("正在获取当前模型信息...")
            model_info = await plugin.get_current_model()
            print(f"当前模型: {model_info.get('modelName', '未知')}")
            
            # 获取可用参数列表
            print("正在获取可用参数列表...")
            parameters = await plugin.get_available_parameters()
            print(f"找到 {len(parameters)} 个可用参数")
            
            # 获取表情列表
            print("正在获取表情列表...")
            expressions = await plugin.get_expressions()
            print(f"找到 {len(expressions)} 个表情")
            
            # 获取动画列表
            print("正在获取动画列表...")
            animations = await plugin.get_animations()
            print(f"找到 {len(animations)} 个动画")
            
        else:
            print("认证失败")
    
    except Exception as e:
        print(f"发生错误: {str(e)}")
    
    finally:
        # 断开连接
        print("正在断开连接...")
        await plugin.disconnect()
        print("已断开连接")

if __name__ == "__main__":
    asyncio.run(main())
