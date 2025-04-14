#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VTube Studio 面部控制插件 - 改进版
使用Live2DParameterListRequest获取参数，解决参数列表为空的问题
"""

import asyncio
import json
import logging
import uuid
import argparse
import websockets
from aiohttp import web
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('VTS_Face_Control')

class VTSPlugin:
    """VTube Studio 插件类"""
    
    def __init__(self, vts_ws_url='ws://localhost:8001', api_port=8080):
        """初始化插件
        
        Args:
            vts_ws_url: VTube Studio WebSocket URL
            api_port: 外部API服务器端口
        """
        self.vts_ws_url = vts_ws_url
        self.api_port = api_port
        self.ws = None
        self.authenticated = False
        self.plugin_name = "VTS面部控制插件"
        self.plugin_author = "Manus"
        self.plugin_id = ""
        self.auth_token = None
        self.ws_connected = False
        
        # 模型信息
        self.model_loaded = False
        self.current_model = None
        self.current_model_id = None
        
        # 参数和表情
        self.tracking_parameters = []  # 跟踪参数（InputParameterListRequest）
        self.live2d_parameters = []    # Live2D参数（Live2DParameterListRequest）
        self.available_parameters = [] # 合并后的可用参数
        self.available_expressions = []
        self.common_parameters = []
        
        # 参数映射（Live2D参数名到跟踪参数名）
        self.parameter_mapping = {
            # 常见的Live2D参数到跟踪参数的映射
            "ParamAngleX": "FaceAngleX",
            "ParamAngleY": "FaceAngleY",
            "ParamAngleZ": "FaceAngleZ",
            "ParamEyeLOpen": "EyeOpenLeft",
            "ParamEyeROpen": "EyeOpenRight",
            "ParamEyeBallX": "EyeLeftX",  # 可能需要调整
            "ParamEyeBallY": "EyeLeftY",  # 可能需要调整
            "ParamMouthOpenY": "MouthOpenY",
            "ParamMouthForm": "MouthSmile",
            "ParamBrowLY": "BrowLeftY",
            "ParamBrowRY": "BrowRightY",
            # 可以根据需要添加更多映射
        }
        
        # 反向映射（跟踪参数名到Live2D参数名）
        self.reverse_mapping = {v: k for k, v in self.parameter_mapping.items()}
    
    async def connect(self):
        """连接到VTube Studio WebSocket服务器"""
        try:
            logger.info(f"正在连接到VTubeStudio: {self.vts_ws_url}")
            self.ws = await websockets.connect(self.vts_ws_url)
            self.ws_connected = True
            logger.info(f"已连接到VTubeStudio: {self.vts_ws_url}")
            return True
        except Exception as e:
            logger.error(f"连接VTubeStudio失败: {e}")
            logger.error(traceback.format_exc())
            self.ws_connected = False
            return False
    
    async def send_request(self, request_type, data=None):
        """发送请求到VTubeStudio
        
        Args:
            request_type: 请求类型
            data: 请求数据
            
        Returns:
            响应数据
        """
        try:
            if not self.ws or not self.ws_connected:
                logger.error("未连接到VTubeStudio")
                return None
                
            request_id = str(uuid.uuid4())
            request = {
                "apiName": "VTubeStudioPublicAPI",
                "apiVersion": "1.0",
                "requestID": request_id,
                "messageType": request_type
            }
            
            if data:
                request["data"] = data
                
            request_json = json.dumps(request)
            logger.debug(f"发送请求: {request_json}")
            await self.ws.send(request_json)
            
            response_text = await self.ws.recv()
            logger.debug(f"收到响应: {response_text}")
            
            try:
                response = json.loads(response_text)
                return response
            except json.JSONDecodeError as e:
                logger.error(f"解析响应JSON失败: {e}")
                logger.error(f"原始响应: {response_text}")
                return None
        except Exception as e:
            logger.error(f"发送请求时出错: {e}")
            logger.error(traceback.format_exc())
            self.ws_connected = False
            return None
    
    async def authenticate(self):
        """向VTubeStudio进行身份验证 - 两步认证流程"""
        try:
            # 获取API状态
            logger.info("正在获取API状态...")
            api_state = await self.send_request("APIStateRequest")
            if not api_state:
                logger.error("获取API状态失败")
                return False
                
            logger.info(f"API状态响应: {json.dumps(api_state, ensure_ascii=False)}")
            is_authenticated = api_state.get('data', {}).get('currentSessionAuthenticated', False)
            logger.info(f"当前认证状态: {is_authenticated}")
            
            # 如果已经认证，则不需要再次认证
            if is_authenticated:
                self.authenticated = True
                logger.info("已经认证，无需再次认证")
                return True
            
            # 第一步：请求认证令牌
            auth_data = {
                "pluginName": self.plugin_name,
                "pluginDeveloper": self.plugin_author,
                "pluginIcon": ""
            }
            
            logger.info(f"发送认证令牌请求: {json.dumps(auth_data, ensure_ascii=False)}")
            token_response = await self.send_request("AuthenticationTokenRequest", auth_data)
            
            if not token_response or 'data' not in token_response:
                logger.error("认证令牌请求失败")
                return False
                
            logger.info(f"认证令牌响应: {json.dumps(token_response, ensure_ascii=False)}")
            
            # 获取认证令牌
            self.auth_token = token_response.get('data', {}).get('authenticationToken')
            if not self.auth_token:
                logger.error("认证令牌为空")
                return False
                
            logger.info(f"获取到认证令牌: {self.auth_token}")
            
            # 第二步：使用令牌进行认证
            auth_request_data = {
                "pluginName": self.plugin_name,
                "pluginDeveloper": self.plugin_author,
                "authenticationToken": self.auth_token
            }
            
            logger.info(f"发送认证请求: {json.dumps(auth_request_data, ensure_ascii=False)}")
            auth_response = await self.send_request("AuthenticationRequest", auth_request_data)
            
            if not auth_response or 'data' not in auth_response:
                logger.error("认证请求失败")
                return False
                
            logger.info(f"认证响应: {json.dumps(auth_response, ensure_ascii=False)}")
            
            # 检查认证状态
            authenticated = auth_response.get('data', {}).get('authenticated', False)
            if authenticated:
                self.authenticated = True
                self.plugin_id = auth_response.get('data', {}).get('pluginId', "")
                logger.info(f"认证成功，插件ID: {self.plugin_id}")
                return True
            else:
                reason = auth_response.get('data', {}).get('reason', "未知原因")
                logger.error(f"认证失败: {reason}")
                return False
                
        except Exception as e:
            logger.error(f"认证过程中出现异常: {e}")
            logger.error(traceback.format_exc())
            return False
    
    async def get_current_model_info(self):
        """获取当前模型信息"""
        if not self.authenticated:
            logger.error("未认证，无法获取模型信息")
            return False
            
        response = await self.send_request("CurrentModelRequest")
        if not response:
            return False
            
        if 'data' in response and 'modelLoaded' in response['data']:
            self.model_loaded = response['data']['modelLoaded']
            if self.model_loaded:
                self.current_model = response['data'].get('modelName', "")
                self.current_model_id = response['data'].get('modelID', "")
                logger.info(f"当前模型: {self.current_model} (ID: {self.current_model_id})")
            else:
                logger.info("当前没有加载模型")
            return True
        return False
    
    async def get_tracking_parameters(self):
        """获取跟踪参数列表（使用InputParameterListRequest）"""
        if not self.authenticated:
            logger.error("未认证，无法获取跟踪参数列表")
            return False
            
        response = await self.send_request("InputParameterListRequest")
        if not response:
            return False
            
        if 'data' in response:
            # 检查是否有默认参数
            default_params = response['data'].get('defaultParameters', [])
            custom_params = response['data'].get('customParameters', [])
            
            # 合并参数列表
            self.tracking_parameters = default_params + custom_params
            logger.info(f"获取到 {len(self.tracking_parameters)} 个跟踪参数")
            
            # 如果参数列表为空，记录警告
            if not self.tracking_parameters:
                logger.warning("跟踪参数列表为空，这可能是VTubeStudio API的限制")
            
            return True
        return False
    
    async def get_live2d_parameters(self):
        """获取Live2D参数列表（使用Live2DParameterListRequest）"""
        if not self.authenticated or not self.model_loaded:
            logger.error("未认证或未加载模型，无法获取Live2D参数列表")
            return False
            
        response = await self.send_request("Live2DParameterListRequest")
        if not response:
            return False
            
        if 'data' in response and 'parameters' in response['data']:
            self.live2d_parameters = response['data']['parameters']
            logger.info(f"获取到 {len(self.live2d_parameters)} 个Live2D参数")
            return True
        return False
    
    async def merge_parameters(self):
        """合并跟踪参数和Live2D参数"""
        # 首先清空合并后的参数列表
        self.available_parameters = []
        
        # 添加跟踪参数
        for param in self.tracking_parameters:
            # 确保参数有name字段
            if 'name' in param:
                self.available_parameters.append(param)
        
        # 添加Live2D参数（如果不在跟踪参数中）
        tracking_param_names = [p.get('name') for p in self.tracking_parameters]
        for param in self.live2d_parameters:
            # 确保参数有name字段
            if 'name' in param:
                # 检查是否已经存在同名参数
                if param['name'] not in tracking_param_names:
                    # 尝试映射Live2D参数到跟踪参数
                    if param['name'] in self.parameter_mapping:
                        # 添加映射信息
                        param['mappedTo'] = self.parameter_mapping[param['name']]
                    
                    self.available_parameters.append(param)
        
        logger.info(f"合并后共有 {len(self.available_parameters)} 个可用参数")
        return True
    
    async def preload_common_parameters(self):
        """预加载常见参数"""
        logger.info("预加载常见参数...")
        self.common_parameters = [
            {"name": "FaceAngleX", "description": "面部水平旋转", "defaultValue": 0},
            {"name": "FaceAngleY", "description": "面部垂直旋转", "defaultValue": 0},
            {"name": "FaceAngleZ", "description": "面部倾斜", "defaultValue": 0},
            {"name": "MouthSmile", "description": "微笑程度", "defaultValue": 0},
            {"name": "MouthOpenY", "description": "嘴巴开合程度", "defaultValue": 0},
            {"name": "EyeOpenLeft", "description": "左眼开合程度", "defaultValue": 1},
            {"name": "EyeOpenRight", "description": "右眼开合程度", "defaultValue": 1},
            {"name": "EyeLeftX", "description": "左眼水平位置", "defaultValue": 0},
            {"name": "EyeLeftY", "description": "左眼垂直位置", "defaultValue": 0},
            {"name": "EyeRightX", "description": "右眼水平位置", "defaultValue": 0},
            {"name": "EyeRightY", "description": "右眼垂直位置", "defaultValue": 0},
            {"name": "BrowLeftY", "description": "左眉毛高度", "defaultValue": 0},
            {"name": "BrowRightY", "description": "右眉毛高度", "defaultValue": 0},
            {"name": "TongueOut", "description": "舌头伸出程度", "defaultValue": 0},
            {"name": "CheekPuff", "description": "脸颊鼓起", "defaultValue": 0},
            {"name": "MouthX", "description": "嘴巴水平位置", "defaultValue": 0}
        ]
        
        # 将常见参数添加到可用参数列表
        if not self.available_parameters:
            self.available_parameters = []
        
        # 只添加不存在的参数
        existing_names = [p.get('name') for p in self.available_parameters]
        for param in self.common_parameters:
            if param["name"] not in existing_names:
                self.available_parameters.append(param)
        
        logger.info(f"预加载了 {len(self.common_parameters)} 个常见参数")
        return True
    
    async def get_available_expressions(self):
        """获取可用表情列表"""
        if not self.authenticated or not self.model_loaded:
            logger.error("未认证或未加载模型，无法获取表情列表")
            return False
            
        response = await self.send_request("ExpressionStateRequest")
        if not response:
            return False
            
        if 'data' in response and 'expressions' in response['data']:
            self.available_expressions = response['data']['expressions']
            logger.info(f"获取到 {len(self.available_expressions)} 个表情")
            return True
        return False
    
    async def set_parameter_value(self, parameter_id, value, weight=1.0):
        """设置参数值
        
        Args:
            parameter_id: 参数ID
            value: 参数值
            weight: 权重，0-1之间
            
        Returns:
            是否成功
        """
        if not self.authenticated:
            logger.error("未认证，无法设置参数值")
            return False
        
        # 检查是否是Live2D参数，如果是则尝试映射到跟踪参数
        mapped_id = parameter_id
        if parameter_id in self.parameter_mapping:
            mapped_id = self.parameter_mapping[parameter_id]
            logger.debug(f"参数映射: {parameter_id} -> {mapped_id}")
        
        data = {
            "faceFound": True,
            "mode": "set",
            "parameterValues": [
                {
                    "id": mapped_id,
                    "value": value,
                    "weight": weight
                }
            ]
        }
        
        response = await self.send_request("InjectParameterDataRequest", data)
        if not response:
            return False
            
        return True
    
    async def set_expression(self, expression_file, active, fade_time=0.5):
        """设置表情
        
        Args:
            expression_file: 表情文件名
            active: 是否激活
            fade_time: 淡入淡出时间
            
        Returns:
            是否成功
        """
        if not self.authenticated or not self.model_loaded:
            logger.error("未认证或未加载模型，无法设置表情")
            return False
            
        data = {
            "expressionFile": expression_file,
            "active": active,
            "fadeTime": fade_time
        }
        
        response = await self.send_request("ExpressionActivationRequest", data)
        if not response:
            return False
            
        return True
    
    async def initialize(self):
        """初始化插件"""
        try:
            # 连接到VTubeStudio
            if not await self.connect():
                logger.error("连接VTubeStudio失败")
                return False
                
            # 认证
            auth_success = await self.authenticate()
            if not auth_success:
                logger.error("认证失败")
                return False
                
            logger.info("认证成功")
            
            # 获取当前模型信息
            await self.get_current_model_info()
            
            # 获取参数列表 - 首先尝试获取跟踪参数
            await self.get_tracking_parameters()
            
            # 如果模型已加载，尝试获取Live2D参数
            if self.model_loaded:
                await self.get_live2d_parameters()
                
                # 合并参数
                await self.merge_parameters()
            
            # 如果参数列表为空，预加载常见参数
            if not self.available_parameters:
                logger.info("参数列表为空，预加载常见参数")
                await self.preload_common_parameters()
            
            # 如果有模型加载，获取可用表情
            if self.model_loaded:
                await self.get_available_expressions()
                
            return True
        except Exception as e:
            logger.error(f"初始化插件时出错: {e}")
            logger.error(traceback.format_exc())
            return False
    
    async def start_api_server(self):
        """启动API服务器"""
        app = web.Application()
        
        # 路由
        app.router.add_get('/', self.handle_root)
        app.router.add_get('/status', self.handle_status)
        app.router.add_get('/parameters', self.handle_get_parameters)
        app.router.add_get('/live2d_parameters', self.handle_get_live2d_parameters)
        app.router.add_get('/tracking_parameters', self.handle_get_tracking_parameters)
        app.router.add_get('/expressions', self.handle_get_expressions)
        app.router.add_post('/parameter', self.handle_set_parameter)
        app.router.add_post('/parameters', self.handle_set_parameters)
        app.router.add_post('/expression', self.handle_set_expression)
        
        # 启动服务器
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.api_port)
        await site.start()
        logger.info(f"API服务器已启动，监听端口: {self.api_port}")
        
        return runner
    
    # API处理函数
    async def handle_root(self, request):
        """处理根路径请求"""
        data = {
            "name": self.plugin_name,
            "author": self.plugin_author,
            "status": "running",
            "authenticated": self.authenticated,
            "model_loaded": self.model_loaded,
            "current_model": self.current_model,
            "endpoints": [
                {"path": "/", "method": "GET", "description": "获取插件信息"},
                {"path": "/status", "method": "GET", "description": "获取状态信息"},
                {"path": "/parameters", "method": "GET", "description": "获取所有可用参数列表"},
                {"path": "/live2d_parameters", "method": "GET", "description": "获取Live2D参数列表"},
                {"path": "/tracking_parameters", "method": "GET", "description": "获取跟踪参数列表"},
                {"path": "/expressions", "method": "GET", "description": "获取可用表情列表"},
                {"path": "/parameter", "method": "POST", "description": "设置单个参数值"},
                {"path": "/parameters", "method": "POST", "description": "设置多个参数值"},
                {"path": "/expression", "method": "POST", "description": "激活或停用表情"}
            ]
        }
        return web.json_response(data)
    
    async def handle_status(self, request):
        """处理状态请求"""
        data = {
            "authenticated": self.authenticated,
            "model_loaded": self.model_loaded,
            "current_model": self.current_model,
            "current_model_id": self.current_model_id,
            "tracking_parameter_count": len(self.tracking_parameters),
            "live2d_parameter_count": len(self.live2d_parameters),
            "available_parameter_count": len(self.available_parameters),
            "expression_count": len(self.available_expressions)
        }
        return web.json_response(data)
    
    async def handle_get_parameters(self, request):
        """处理获取所有可用参数列表请求"""
        # 刷新参数列表
        if self.model_loaded:
            # 尝试获取跟踪参数
            await self.get_tracking_parameters()
            
            # 尝试获取Live2D参数
            await self.get_live2d_parameters()
            
            # 合并参数
            await self.merge_parameters()
        else:
            # 只获取跟踪参数
            await self.get_tracking_parameters()
        
        # 如果参数列表为空，预加载常见参数
        if not self.available_parameters:
            logger.info("参数列表为空，预加载常见参数")
            await self.preload_common_parameters()
            
        return web.json_response({"parameters": self.available_parameters})
    
    async def handle_get_live2d_parameters(self, request):
        """处理获取Live2D参数列表请求"""
        if not self.model_loaded:
            return web.json_response({"error": "未加载模型"}, status=400)
            
        await self.get_live2d_parameters()
        return web.json_response({"parameters": self.live2d_parameters})
    
    async def handle_get_tracking_parameters(self, request):
        """处理获取跟踪参数列表请求"""
        await self.get_tracking_parameters()
        return web.json_response({"parameters": self.tracking_parameters})
    
    async def handle_get_expressions(self, request):
        """处理获取表情列表请求"""
        if not self.model_loaded:
            return web.json_response({"error": "未加载模型"}, status=400)
            
        await self.get_available_expressions()
        return web.json_response({"expressions": self.available_expressions})
    
    async def handle_set_parameter(self, request):
        """处理设置参数请求"""
        try:
            data = await request.json()
            parameter_id = data.get('id')
            value = data.get('value')
            weight = data.get('weight', 1.0)
            
            if not parameter_id or value is None:
                return web.json_response({"error": "缺少参数ID或值"}, status=400)
                
            success = await self.set_parameter_value(parameter_id, value, weight)
            if success:
                return web.json_response({"success": True})
            else:
                return web.json_response({"error": "设置参数失败"}, status=500)
        except Exception as e:
            logger.error(f"处理设置参数请求时出错: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_set_parameters(self, request):
        """处理设置多个参数请求"""
        try:
            data = await request.json()
            parameters = data.get('parameters', [])
            
            if not parameters:
                return web.json_response({"error": "缺少参数列表"}, status=400)
                
            # 构建参数值列表
            param_values = []
            for param in parameters:
                param_id = param.get('id')
                value = param.get('value')
                weight = param.get('weight', 1.0)
                
                if not param_id or value is None:
                    continue
                
                # 检查是否是Live2D参数，如果是则尝试映射到跟踪参数
                mapped_id = param_id
                if param_id in self.parameter_mapping:
                    mapped_id = self.parameter_mapping[param_id]
                    logger.debug(f"参数映射: {param_id} -> {mapped_id}")
                    
                param_values.append({
                    "id": mapped_id,
                    "value": value,
                    "weight": weight
                })
            
            if not param_values:
                return web.json_response({"error": "没有有效的参数"}, status=400)
                
            # 发送请求
            data = {
                "faceFound": True,
                "mode": "set",
                "parameterValues": param_values
            }
            
            response = await self.send_request("InjectParameterDataRequest", data)
            if response:
                return web.json_response({"success": True})
            else:
                return web.json_response({"error": "设置参数失败"}, status=500)
        except Exception as e:
            logger.error(f"处理设置多个参数请求时出错: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_set_expression(self, request):
        """处理设置表情请求"""
        try:
            if not self.model_loaded:
                return web.json_response({"error": "未加载模型"}, status=400)
                
            data = await request.json()
            expression_file = data.get('file')
            active = data.get('active')
            fade_time = data.get('fade_time', 0.5)
            
            if not expression_file or active is None:
                return web.json_response({"error": "缺少表情文件或激活状态"}, status=400)
                
            success = await self.set_expression(expression_file, active, fade_time)
            if success:
                return web.json_response({"success": True})
            else:
                return web.json_response({"error": "设置表情失败"}, status=500)
        except Exception as e:
            logger.error(f"处理设置表情请求时出错: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def check_connection(self):
        """检查WebSocket连接状态"""
        if not self.ws:
            return False
            
        try:
            # 尝试发送一个ping来检查连接
            pong = await self.ws.ping()
            await asyncio.wait_for(pong, timeout=5)
            self.ws_connected = True
            return True
        except Exception as e:
            logger.warning(f"WebSocket连接检查失败: {e}")
            self.ws_connected = False
            return False

async def main():
    """主函数"""
    try:
        parser = argparse.ArgumentParser(description='VTubeStudio面部控制插件')
        parser.add_argument('--vts-url', default='ws://localhost:8001', help='VTubeStudio WebSocket URL')
        parser.add_argument('--api-port', type=int, default=8080, help='外部API服务器端口')
        parser.add_argument('--debug', action='store_true', help='启用调试日志')
        args = parser.parse_args()
        
        # 设置日志级别
        if args.debug:
            logger.setLevel(logging.DEBUG)
        
        # 创建插件实例
        plugin = VTSPlugin(vts_ws_url=args.vts_url, api_port=args.api_port)
        
        # 初始化插件
        init_success = await plugin.initialize()
        if not init_success:
            logger.error("插件初始化失败")
            return
        
        # 启动API服务器
        runner = await plugin.start_api_server()
        
        try:
            # 保持运行
            while True:
                try:
                    # 每隔一段时间刷新模型信息和参数列表
                    await asyncio.sleep(30)
                    
                    # 检查连接状态
                    connection_ok = await plugin.check_connection()
                    if not connection_ok:
                        logger.warning("WebSocket连接已断开，尝试重新连接...")
                        await plugin.connect()
                        if plugin.ws_connected:
                            await plugin.authenticate()
                    
                    # 刷新信息
                    if plugin.authenticated:
                        await plugin.get_current_model_info()
                        
                        # 如果模型已加载，刷新参数和表情
                        if plugin.model_loaded:
                            # 获取跟踪参数
                            await plugin.get_tracking_parameters()
                            
                            # 获取Live2D参数
                            await plugin.get_live2d_parameters()
                            
                            # 合并参数
                            await plugin.merge_parameters()
                            
                            # 如果参数列表为空，预加载常见参数
                            if not plugin.available_parameters:
                                await plugin.preload_common_parameters()
                                
                            # 获取表情列表
                            await plugin.get_available_expressions()
                except Exception as e:
                    logger.error(f"刷新信息时出错: {e}")
                    logger.error(traceback.format_exc())
        except KeyboardInterrupt:
            logger.info("接收到中断信号，正在关闭...")
        finally:
            # 清理资源
            if plugin.ws:
                await plugin.ws.close()
            await runner.cleanup()
    except Exception as e:
        logger.error(f"主函数出错: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())
