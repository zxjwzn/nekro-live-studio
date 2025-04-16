#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VTube Studio 面部控制插件 - 改进版
使用Live2DParameterListRequest获取参数，解决参数列表为空的问题
添加了动画控制功能
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
        
        # 场景中的物品
        self.scene_items = []
        
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
    
    async def get_items_in_scene(self):
        """获取场景中的物品列表"""
        if not self.authenticated:
            logger.error("未认证，无法获取场景物品列表")
            return False
            
        response = await self.send_request("ItemListRequest", {"includeAvailableSpots": False, "includeItemInstancesInScene": True})
        if not response:
            return False
            
        if 'data' in response and 'itemInstancesInScene' in response['data']:
            self.scene_items = response['data']['itemInstancesInScene']
            logger.info(f"获取到 {len(self.scene_items)} 个场景物品")
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
    
    async def control_item_animation(self, item_instance_id, play_animation=None, frame_rate=None, frame=None, auto_stop_frames=None):
        """控制物品动画
        
        Args:
            item_instance_id: 物品实例ID
            play_animation: 是否播放动画 (True/False)
            frame_rate: 帧率 (0.1-120)
            frame: 跳转到指定帧
            auto_stop_frames: 自动停止帧列表
            
        Returns:
            是否成功
        """
        if not self.authenticated:
            logger.error("未认证，无法控制物品动画")
            return False
            
        data = {
            "itemInstanceID": item_instance_id,
            "brightness": -1,  # 不改变亮度
            "opacity": -1,     # 不改变不透明度
        }
        
        # 设置动画播放状态
        if play_animation is not None:
            data["animationPlayState"] = play_animation
            data["setAnimationPlayState"] = True
        
        # 设置帧率
        if frame_rate is not None:
            # 确保帧率在有效范围内
            frame_rate = max(0.1, min(120, frame_rate))
            data["framerate"] = frame_rate
        
        # 设置当前帧
        if frame is not None:
            data["frame"] = frame
        
        # 设置自动停止帧
        if auto_stop_frames is not None:
            data["autoStopFrames"] = auto_stop_frames
            data["setAutoStopFrames"] = True
        
        response = await self.send_request("ItemAnimationControlRequest", data)
        if not response:
            return False
        
        # 检查响应是否成功
        if 'data' in response and 'success' in response['data']:
            success = response['data']['success']
            if not success and 'errorID' in response['data']:
                error_id = response['data']['errorID']
                logger.error(f"控制物品动画失败，错误ID: {error_id}")
                return False
            return success
        return False
    
    async def play_item_animation(self, item_instance_id, frame_rate=30.0):
        """播放物品动画
        
        Args:
            item_instance_id: 物品实例ID
            frame_rate: 帧率 (0.1-120)
            
        Returns:
            是否成功
        """
        return await self.control_item_animation(
            item_instance_id=item_instance_id,
            play_animation=True,
            frame_rate=frame_rate
        )
    
    async def stop_item_animation(self, item_instance_id):
        """停止物品动画
        
        Args:
            item_instance_id: 物品实例ID
            
        Returns:
            是否成功
        """
        return await self.control_item_animation(
            item_instance_id=item_instance_id,
            play_animation=False
        )
    
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
                
            # 如果模型已加载，获取表情列表
            if self.model_loaded:
                await self.get_available_expressions()
                
            # 获取场景中的物品列表
            await self.get_items_in_scene()
                
            return True
        except Exception as e:
            logger.error(f"初始化插件时出错: {e}")
            logger.error(traceback.format_exc())
            return False
    
    async def disconnect(self):
        """断开与VTubeStudio的连接"""
        if self.ws:
            await self.ws.close()
            self.ws = None
            self.ws_connected = False
            logger.info("已断开与VTubeStudio的连接")
    
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
    
    async def start_api_server(self):
        """启动API服务器"""
        app = web.Application()
        
        # 路由
        app.router.add_get('/', self.handle_root)
        app.router.add_get('/status', self.handle_get_status)
        app.router.add_get('/parameters', self.handle_get_parameters)
        app.router.add_get('/expressions', self.handle_get_expressions)
        app.router.add_get('/items', self.handle_get_items)
        app.router.add_post('/parameter', self.handle_set_parameter)
        app.router.add_post('/parameters', self.handle_set_parameters)
        app.router.add_post('/expression', self.handle_set_expression)
        app.router.add_post('/animation/play', self.handle_play_animation)
        app.router.add_post('/animation/stop', self.handle_stop_animation)
        app.router.add_post('/animation/control', self.handle_control_animation)
        
        # 启动服务器
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.api_port)
        await site.start()
        logger.info(f"API服务器已启动，监听端口: {self.api_port}")
        
        # 保持服务器运行
        while True:
            try:
                # 检查连接状态
                connection_ok = await self.check_connection()
                if not connection_ok:
                    logger.warning("WebSocket连接已断开，尝试重新连接...")
                    await self.connect()
                    if self.ws_connected:
                        await self.authenticate()
                
                # 刷新信息
                if self.authenticated:
                    await self.get_current_model_info()
                    await self.get_tracking_parameters()
                    
                    if self.model_loaded:
                        await self.get_live2d_parameters()
                        await self.merge_parameters()
                        await self.get_available_expressions()
                        await self.get_items_in_scene()
                    
                    # 如果参数列表为空，预加载常见参数
                    if not self.available_parameters:
                        await self.preload_common_parameters()
                
                # 等待一段时间
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"API服务器循环中出错: {e}")
                logger.error(traceback.format_exc())
                await asyncio.sleep(5)
    
    # API处理函数
    
    async def handle_root(self, request):
        """处理根路径请求"""
        return web.json_response({
            "name": self.plugin_name,
            "developer": self.plugin_author,
            "authenticated": self.authenticated,
            "modelLoaded": self.model_loaded,
            "currentModel": self.current_model
        })
    
    async def handle_get_status(self, request):
        """处理获取状态请求"""
        return web.json_response({
            "authenticated": self.authenticated,
            "model_loaded": self.model_loaded,
            "current_model": self.current_model,
            "current_model_id": self.current_model_id,
            "parameter_count": len(self.available_parameters),
            "expression_count": len(self.available_expressions),
            "item_count": len(self.scene_items)
        })
    
    async def handle_get_parameters(self, request):
        """处理获取参数列表请求"""
        await self.get_tracking_parameters()
        
        if self.model_loaded:
            await self.get_live2d_parameters()
            await self.merge_parameters()
        
        # 如果参数列表为空，预加载常见参数
        if not self.available_parameters:
            logger.info("参数列表为空，预加载常见参数")
            await self.preload_common_parameters()
            
        return web.json_response({"parameters": self.available_parameters})
    
    async def handle_get_expressions(self, request):
        """处理获取表情列表请求"""
        if not self.model_loaded:
            return web.json_response({"error": "未加载模型"}, status=400)
            
        await self.get_available_expressions()
        return web.json_response({"expressions": self.available_expressions})
    
    async def handle_get_items(self, request):
        """处理获取物品列表请求"""
        await self.get_items_in_scene()
        return web.json_response({"items": self.scene_items})
    
    async def activate_expression(self, expression_file: str, active: bool = True, fade_time: float = 0.5) -> bool:
        """激活或停用表情
        
        Args:
            expression_file: 表情文件名，必须包含.exp3.json后缀
            active: 是否激活表情
            fade_time: 淡入淡出时间（秒）
            
        Returns:
            操作是否成功
        """
        if not self.authenticated:
            logger.error("未认证，无法控制表情")
            return False
        
        if not self.model_loaded:
            logger.warning("未加载模型，无法控制表情")
            return False
        
        # 确保文件名包含.exp3.json后缀
        if not expression_file.endswith(".exp3.json"):
            logger.warning(f"表情文件名必须包含.exp3.json后缀: {expression_file}")
            expression_file += ".exp3.json"
        
        response = await self.send_request("ExpressionActivationRequest", {
            "expressionFile": expression_file,
            "active": active,
            "fadeTime": fade_time
        })
        
        if not response:
            return False
        
        success = not response.get("data", {}).get("error", False)
        if success:
            logger.info(f"{'激活' if active else '停用'}表情成功: {expression_file}")
        else:
            error_message = response.get("data", {}).get("message", "未知错误")
            logger.error(f"{'激活' if active else '停用'}表情失败: {error_message}")
        
        return success
    
    async def _auto_stop_animation(self, animation_file: str, delay: float):
        """自动停止动画
        
        Args:
            animation_file: 表情文件名
            delay: 延迟时间（秒）
        """
        await asyncio.sleep(delay)
        await self.activate_expression(animation_file, False, 0.5)
        logger.info(f"自动停止动画: {animation_file}")

    async def handle_play_animation(self, request):
        """处理播放动画请求（通过表情系统）"""
        try:
            data = await request.json()
            animation_file = data.get("file")  # 表情文件名
            fade_time = data.get("fadeTime", 0.5)
            auto_stop = data.get("autoStop", False)
            stop_after = data.get("stopAfter", 0)  # 自动停止时间（秒）
            
            if not animation_file:
                return web.json_response({"error": "缺少动画文件名"}, status=400)
            
            # 激活表情
            success = await self.activate_expression(animation_file, True, fade_time)
            
            # 如果需要自动停止
            if success and auto_stop and stop_after > 0:
                # 创建一个任务，在指定时间后停止表情
                asyncio.create_task(self._auto_stop_animation(animation_file, stop_after))
            
            return web.json_response({"success": success})
        except Exception as e:
            logger.error(f"处理播放动画请求时出错: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_stop_animation(self, request):
        """处理停止动画请求（通过表情系统）"""
        try:
            data = await request.json()
            animation_file = data.get("file")  # 表情文件名
            fade_time = data.get("fadeTime", 0.5)
            
            if not animation_file:
                return web.json_response({"error": "缺少动画文件名"}, status=400)
            
            # 停用表情
            success = await self.activate_expression(animation_file, False, fade_time)
            return web.json_response({"success": success})
        except Exception as e:
            logger.error(f"处理停止动画请求时出错: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def handle_set_parameter(self, request):
        """处理设置参数请求"""
        try:
            data = await request.json()
            
            if 'id' not in data or 'value' not in data:
                return web.json_response({"error": "缺少必要参数"}, status=400)
                
            parameter_id = data['id']
            value = float(data['value'])
            weight = float(data.get('weight', 1.0))
            
            result = await self.set_parameter_value(parameter_id, value, weight)
            
            return web.json_response({"success": result})
        except Exception as e:
            logger.error(f"处理设置参数请求时出错: {e}")
            logger.error(traceback.format_exc())
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_set_parameters(self, request):
        """处理设置多个参数请求"""
        try:
            data = await request.json()
            
            if 'parameters' not in data or not isinstance(data['parameters'], list):
                return web.json_response({"error": "缺少必要参数"}, status=400)
                
            parameters = data['parameters']
            
            # 构建参数值列表
            param_values = []
            for param in parameters:
                if 'id' in param and 'value' in param:
                    param_id = param['id']
                    value = float(param['value'])
                    weight = float(param.get('weight', 1.0))
                    
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
            
            if not response:
                return web.json_response({"success": False, "error": "请求失败"})
                
            return web.json_response({"success": True})
        except Exception as e:
            logger.error(f"处理设置多个参数请求时出错: {e}")
            logger.error(traceback.format_exc())
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_set_expression(self, request):
        """处理设置表情请求"""
        try:
            data = await request.json()
            
            if 'file' not in data or 'active' not in data:
                return web.json_response({"error": "缺少必要参数"}, status=400)
                
            expression_file = data['file']
            active = data['active']
            fade_time = float(data.get('fadeTime', 0.5))
            
            result = await self.set_expression(expression_file, active, fade_time)
            
            return web.json_response({"success": result})
        except Exception as e:
            logger.error(f"处理设置表情请求时出错: {e}")
            logger.error(traceback.format_exc())
            return web.json_response({"error": str(e)}, status=500)
    
    
    
    async def handle_control_animation(self, request):
        """处理控制动画请求"""
        try:
            data = await request.json()
            
            if 'itemInstanceID' not in data:
                return web.json_response({"error": "缺少必要参数"}, status=400)
                
            item_instance_id = data['itemInstanceID']
            play_animation = data.get('playAnimation')
            frame_rate = data.get('frameRate')
            frame = data.get('frame')
            auto_stop_frames = data.get('autoStopFrames')
            
            result = await self.control_item_animation(
                item_instance_id=item_instance_id,
                play_animation=play_animation,
                frame_rate=frame_rate,
                frame=frame,
                auto_stop_frames=auto_stop_frames
            )
            
            return web.json_response({"success": result})
        except Exception as e:
            logger.error(f"处理控制动画请求时出错: {e}")
            logger.error(traceback.format_exc())
            return web.json_response({"error": str(e)}, status=500)

async def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='VTube Studio 面部控制插件')
    parser.add_argument('--ws-url', type=str, default='ws://localhost:8001', help='VTube Studio WebSocket URL')
    parser.add_argument('--api-port', type=int, default=8080, help='API服务器端口')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    args = parser.parse_args()
    
    # 设置日志级别
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # 创建插件实例
    plugin = VTSPlugin(vts_ws_url=args.ws_url, api_port=args.api_port)
    
    try:
        # 初始化插件
        if not await plugin.initialize():
            logger.error("插件初始化失败")
            return
            
        # 启动API服务器
        await plugin.start_api_server()
    except KeyboardInterrupt:
        logger.info("接收到中断信号，正在关闭...")
    finally:
        # 断开连接
        await plugin.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
