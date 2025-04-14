#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VTube Studio 面部控制插件测试脚本
用于测试插件的各项功能
"""

import asyncio
import json
import aiohttp
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('VTS_Plugin_Test')

class VTSPluginTester:
    """VTube Studio 插件测试类"""
    
    def __init__(self, api_url='http://localhost:8080'):
        """初始化测试类
        
        Args:
            api_url: 插件API URL
        """
        self.api_url = api_url
        self.session = None
    
    async def setup(self):
        """设置测试环境"""
        self.session = aiohttp.ClientSession()
    
    async def teardown(self):
        """清理测试环境"""
        if self.session:
            await self.session.close()
    
    async def get_plugin_info(self):
        """获取插件信息"""
        logger.info("测试: 获取插件信息")
        async with self.session.get(f"{self.api_url}/") as response:
            if response.status == 200:
                data = await response.json()
                logger.info(f"插件信息: {json.dumps(data, ensure_ascii=False, indent=2)}")
                return data
            else:
                error_text = await response.text()
                logger.error(f"获取插件信息失败: {response.status} - {error_text}")
                return None
    
    async def get_status(self):
        """获取状态信息"""
        logger.info("测试: 获取状态信息")
        async with self.session.get(f"{self.api_url}/status") as response:
            if response.status == 200:
                data = await response.json()
                logger.info(f"状态信息: {json.dumps(data, ensure_ascii=False, indent=2)}")
                return data
            else:
                error_text = await response.text()
                logger.error(f"获取状态信息失败: {response.status} - {error_text}")
                return None
    
    async def get_parameters(self):
        """获取参数列表"""
        logger.info("测试: 获取参数列表")
        async with self.session.get(f"{self.api_url}/parameters") as response:
            if response.status == 200:
                data = await response.json()
                parameters = data.get('parameters', [])
                logger.info(f"获取到 {len(parameters)} 个参数")
                if len(parameters) == 0:
                    logger.warning("参数列表为空，这可能是正常的，如果当前没有加载模型或模型没有定义参数")
                    # 尝试获取原始响应内容以进行调试
                    logger.info(f"原始响应: {json.dumps(data, ensure_ascii=False)}")
                return data
            else:
                error_text = await response.text()
                logger.error(f"获取参数列表失败: {response.status} - {error_text}")
                return None
    
    async def get_expressions(self):
        """获取表情列表"""
        logger.info("测试: 获取表情列表")
        async with self.session.get(f"{self.api_url}/expressions") as response:
            if response.status == 200:
                data = await response.json()
                expressions = data.get('expressions', [])
                logger.info(f"获取到 {len(expressions)} 个表情")
                if len(expressions) == 0:
                    logger.warning("表情列表为空，这可能是正常的，如果当前没有加载模型或模型没有定义表情")
                return data
            else:
                error_text = await response.text()
                logger.error(f"获取表情列表失败: {response.status} - {error_text}")
                return None
    
    async def set_parameter(self, parameter_id, value, weight=1.0):
        """设置参数值"""
        logger.info(f"测试: 设置参数 {parameter_id} = {value} (权重: {weight})")
        data = {
            "id": parameter_id,
            "value": value,
            "weight": weight
        }
        async with self.session.post(f"{self.api_url}/parameter", json=data) as response:
            if response.status == 200:
                result = await response.json()
                logger.info(f"设置参数结果: {json.dumps(result, ensure_ascii=False)}")
                return result
            else:
                error_text = await response.text()
                logger.error(f"设置参数失败: {response.status} - {error_text}")
                return None
    
    async def set_parameters(self, parameters):
        """设置多个参数值"""
        logger.info(f"测试: 设置 {len(parameters)} 个参数")
        data = {
            "parameters": parameters
        }
        async with self.session.post(f"{self.api_url}/parameters", json=data) as response:
            if response.status == 200:
                result = await response.json()
                logger.info(f"设置多个参数结果: {json.dumps(result, ensure_ascii=False)}")
                return result
            else:
                error_text = await response.text()
                logger.error(f"设置多个参数失败: {response.status} - {error_text}")
                return None
    
    async def set_expression(self, expression_file, active, fade_time=0.5):
        """设置表情"""
        logger.info(f"测试: {'激活' if active else '停用'} 表情 {expression_file} (淡入淡出时间: {fade_time})")
        data = {
            "file": expression_file,
            "active": active,
            "fade_time": fade_time
        }
        async with self.session.post(f"{self.api_url}/expression", json=data) as response:
            if response.status == 200:
                result = await response.json()
                logger.info(f"设置表情结果: {json.dumps(result, ensure_ascii=False)}")
                return result
            else:
                error_text = await response.text()
                logger.error(f"设置表情失败: {response.status} - {error_text}")
                return None
    
    async def run_tests(self):
        """运行所有测试"""
        try:
            await self.setup()
            
            # 测试获取插件信息
            plugin_info = await self.get_plugin_info()
            if not plugin_info:
                logger.error("获取插件信息失败，终止测试")
                return False
            
            # 测试获取状态信息
            status = await self.get_status()
            if not status:
                logger.error("获取状态信息失败，终止测试")
                return False
                
            # 添加延迟，确保认证状态完全生效
            logger.info("等待3秒，确保认证状态生效...")
            await asyncio.sleep(3)
            
            # 测试获取参数列表
            parameters_data = await self.get_parameters()
            if not parameters_data:
                logger.error("获取参数列表失败，终止测试")
                return False
            
            parameters = parameters_data.get('parameters', [])
            
            # 如果参数列表为空，尝试再次获取
            if len(parameters) == 0:
                #logger.info("参数列表为空，尝试再次获取...")
                await asyncio.sleep(2)
                parameters_data = await self.get_parameters()
                if parameters_data:
                    parameters = parameters_data.get('parameters', [])
                    #logger.info(f"第二次尝试获取到 {len(parameters)} 个参数")
            
            # 打印当前状态信息以帮助诊断
            logger.info(f"当前状态: 模型已加载={status.get('model_loaded', False)}, 模型名称={status.get('current_model', 'None')}")
            
            # 测试获取表情列表
            expressions_data = await self.get_expressions()
            expressions = []
            if expressions_data:
                expressions = expressions_data.get('expressions', [])
            
            # 如果有参数，测试设置参数
            if parameters:
                # 测试设置单个参数
                param = parameters[0]
                param_id = param.get('name')
                param_value = 0.5  # 测试值
                
                result = await self.set_parameter(param_id, param_value)
                if not result or not result.get('success'):
                    logger.error("设置单个参数失败")
                
                # 测试设置多个参数
                if len(parameters) >= 2:
                    params_to_set = [
                        {"id": parameters[0].get('name'), "value": 0.3},
                        {"id": parameters[1].get('name'), "value": 0.7}
                    ]
                    
                    result = await self.set_parameters(params_to_set)
                    if not result or not result.get('success'):
                        logger.error("设置多个参数失败")
            else:
                logger.warning("没有可用参数，跳过参数设置测试")
                
                # 尝试使用一些常见参数名称
                common_params = ["FaceAngleX", "FaceAngleY", "MouthOpenY", "EyeOpenLeft", "EyeOpenRight"]
                #logger.info(f"尝试使用常见参数名称: {common_params[0]}")
                result = await self.set_parameter(common_params[0], 0.5)
                if result and result.get('success'):
                    logger.info(f"成功设置常见参数: {common_params[0]}")
            
            # 如果有表情，测试设置表情
            if expressions:
                expression_file = expressions[0].get('file')
                
                # 激活表情
                result = await self.set_expression(expression_file, True)
                if not result or not result.get('success'):
                    logger.error("激活表情失败")
                
                # 等待2秒
                await asyncio.sleep(2)
                
                # 停用表情
                result = await self.set_expression(expression_file, False)
                if not result or not result.get('success'):
                    logger.error("停用表情失败")
            else:
                logger.warning("没有可用表情，跳过表情设置测试")
            
            logger.info("所有测试完成")
            return True
        except Exception as e:
            logger.error(f"测试过程中出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        finally:
            await self.teardown()

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='VTube Studio 插件测试')
    parser.add_argument('--url', default='http://localhost:8080', help='插件API URL')
    parser.add_argument('--wait', type=int, default=0, help='启动前等待的秒数')
    args = parser.parse_args()
    
    if args.wait > 0:
        logger.info(f"等待 {args.wait} 秒后开始测试...")
        await asyncio.sleep(args.wait)
    
    tester = VTSPluginTester(api_url=args.url)
    await tester.run_tests()

if __name__ == "__main__":
    asyncio.run(main())
