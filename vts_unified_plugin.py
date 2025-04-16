#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VTube Studio 统一控制插件
合并了面部控制、表情、热键和物品动画控制功能
"""

import asyncio
import json
import logging
import uuid
import argparse
import websockets
from aiohttp import web
import traceback
import time
from typing import List, Dict, Any, Optional, Union

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - VTS_Unified_Plugin - %(levelname)s - %(message)s'
)
logger = logging.getLogger('VTS_Unified_Plugin')

class VTSUnifiedPlugin:
    """VTube Studio 统一插件类"""
    
    def __init__(self, 
                 plugin_name: str = "VTS Unified Plugin", 
                 plugin_developer: str = "Manus AI", 
                 vts_ws_url: str = 'ws://localhost:8001', 
                 api_port: int = 8080):
        """初始化插件
        
        Args:
            plugin_name: 插件名称
            plugin_developer: 插件开发者
            vts_ws_url: VTube Studio WebSocket URL
            api_port: 外部API服务器端口
        """
        self.plugin_name = plugin_name
        self.plugin_developer = plugin_developer
        self.vts_ws_url = vts_ws_url
        self.api_port = api_port
        
        # WebSocket & Authentication
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.ws_connected = False
        self.authenticated = False
        self.auth_token: Optional[str] = None
        self.plugin_id: Optional[str] = None
        
        # Model Info
        self.model_loaded = False
        self.current_model: Optional[str] = None
        self.current_model_id: Optional[str] = None
        
        # Parameters & Expressions
        self.tracking_parameters: List[Dict[str, Any]] = []
        self.live2d_parameters: List[Dict[str, Any]] = []
        self.available_parameters: List[Dict[str, Any]] = []
        self.available_expressions: List[Dict[str, Any]] = []
        self.available_hotkeys: List[Dict[str, Any]] = []
        self.common_parameters: List[Dict[str, Any]] = []
        
        # Scene Items
        self.scene_items: List[Dict[str, Any]] = []
        
        # Parameter Mapping (Live2D -> Tracking)
        self.parameter_mapping: Dict[str, str] = {
            "ParamAngleX": "FaceAngleX",
            "ParamAngleY": "FaceAngleY",
            "ParamAngleZ": "FaceAngleZ",
            "ParamEyeLOpen": "EyeOpenLeft",
            "ParamEyeROpen": "EyeOpenRight",
            "ParamEyeBallX": "EyeLeftX", 
            "ParamEyeBallY": "EyeLeftY",
            "ParamMouthOpenY": "MouthOpenY",
            "ParamMouthForm": "MouthSmile",
            "ParamBrowLY": "BrowLeftY",
            "ParamBrowRY": "BrowRightY",
        }
        # Reverse Mapping (Tracking -> Live2D)
        self.reverse_mapping: Dict[str, str] = {v: k for k, v in self.parameter_mapping.items()}
        
        # Request ID Counter (optional, using UUID as primary)
        self.request_counter = 0

    # --- WebSocket and Core Communication ---
    
    async def connect(self) -> bool:
        """连接到VTube Studio WebSocket服务器"""
        try:
            logger.info(f"正在连接到VTubeStudio: {self.vts_ws_url}")
            self.ws = await websockets.connect(self.vts_ws_url)
            self.ws_connected = True
            logger.info(f"已连接到VTubeStudio: {self.vts_ws_url}")
            return True
        except Exception as e:
            logger.error(f"连接VTubeStudio失败: {e}")
            logger.debug(traceback.format_exc())
            self.ws_connected = False
            return False
    
    async def disconnect(self) -> bool:
        """断开与VTubeStudio的连接"""
        if self.ws:
            await self.ws.close()
            self.ws = None
        self.ws_connected = False
        self.authenticated = False
        self.auth_token = None
        self.plugin_id = None
        logger.info("已断开与VTubeStudio的连接")
        return True
    
    async def check_connection(self) -> bool:
        """检查WebSocket连接状态"""
        if not self.ws or not self.ws_connected:
            return False
        try:
            pong = await self.ws.ping()
            await asyncio.wait_for(pong, timeout=5)
            self.ws_connected = True
            return True
        except asyncio.TimeoutError:
            logger.warning("WebSocket ping 超时")
            self.ws_connected = False
            return False
        except Exception as e:
            logger.warning(f"WebSocket连接检查失败: {e}")
            self.ws_connected = False
            return False
            
    async def send_request(self, message_type: str, data: Dict = None) -> Optional[Dict]:
        """发送请求到VTubeStudio
        
        Args:
            message_type: 请求类型
            data: 请求数据
            
        Returns:
            响应数据或None（如果出错）
        """
        if not self.ws or not self.ws_connected:
            logger.error("未连接到VTubeStudio，无法发送请求")
            return None
            
        request_id = str(uuid.uuid4())
        # self.request_counter += 1
        # request_id = f"req_{self.request_counter}_{int(time.time())}" # Alternative ID generation
        
        request = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": request_id,
            "messageType": message_type
        }
        
        if data:
            request["data"] = data
            
        request_json = json.dumps(request)
        logger.debug(f"发送请求: {request_json[:500]}...") # Log truncated request
        
        try:
            await self.ws.send(request_json)
            response_text = await self.ws.recv()
            logger.debug(f"收到响应: {response_text[:500]}...") # Log truncated response
            
            try:
                response = json.loads(response_text)
                
                # Basic error checking
                if response.get("messageType") == "APIError":
                   error_data = response.get("data", {})
                   error_id = error_data.get("errorID")
                   error_msg = error_data.get("message", "未知API错误")
                   logger.error(f"API错误: ID={error_id}, 消息={error_msg}")
                   return None
                   
                # Check if response type matches request type
                # if response.get("messageType") != message_type + "Response":
                #     logger.warning(f"响应类型与请求类型不匹配: 预期 {message_type}Response, 收到 {response.get('messageType')}")
                    # Allow processing even if type doesn't strictly match, as some errors might come this way

                return response
            except json.JSONDecodeError as e:
                logger.error(f"解析响应JSON失败: {e}")
                logger.error(f"原始响应: {response_text}")
                return None
        except websockets.exceptions.ConnectionClosedError as e:
             logger.error(f"WebSocket连接已关闭: {e}")
             self.ws_connected = False
             await self.disconnect()
             return None
        except Exception as e:
            logger.error(f"发送/接收请求时出错: {e}")
            logger.debug(traceback.format_exc())
            # Consider attempting reconnect on certain errors
            # self.ws_connected = False 
            return None

    async def authenticate(self) -> bool:
        """向VTubeStudio进行身份验证"""
        try:
            # 1. 获取API状态，检查是否已认证
            logger.info("正在获取API状态...")
            api_state = await self.send_request("APIStateRequest")
            if api_state and api_state.get('data', {}).get('currentSessionAuthenticated', False):
                 logger.info("已经认证，无需再次认证")
                 self.authenticated = True
                 # Optionally, store plugin ID if needed from state
                 # self.plugin_id = api_state.get('data', {}).get('connectedPlugins', []) # Requires parsing
                 return True

            # 2. 请求认证令牌
            logger.info("请求认证令牌...")
            token_response = await self.send_request("AuthenticationTokenRequest", {
                "pluginName": self.plugin_name,
                "pluginDeveloper": self.plugin_developer,
                "pluginIcon": "" # Optional icon
            })
            
            if not token_response or 'data' not in token_response:
                logger.error("认证令牌请求失败或响应格式错误")
                return False
                
            auth_token = token_response.get('data', {}).get('authenticationToken')
            if not auth_token:
                logger.error("认证令牌为空")
                return False
                
            self.auth_token = auth_token
            logger.info(f"获取到认证令牌: {self.auth_token[:8]}...") # Log partial token
            logger.info("请在VTubeStudio中授权此插件...")
            
            # 3. 使用令牌进行认证 (VTS requires user interaction here)
            auth_response = await self.send_request("AuthenticationRequest", {
                "pluginName": self.plugin_name,
                "pluginDeveloper": self.plugin_developer,
                "authenticationToken": self.auth_token
            })
            
            # Check response after potential user delay
            if not auth_response or 'data' not in auth_response:
                # This might happen if user denies or request times out
                logger.error("认证请求失败或响应格式错误 (用户是否已授权?)")
                return False
                
            authenticated = auth_response.get('data', {}).get('authenticated', False)
            if authenticated:
                self.authenticated = True
                self.plugin_id = auth_response.get('data', {}).get('pluginID')
                logger.info(f"认证成功！ 插件ID: {self.plugin_id}")
                return True
            else:
                reason = auth_response.get('data', {}).get('reason', "未知原因")
                logger.error(f"认证失败: {reason}")
                self.auth_token = None # Clear invalid token
                return False
                
        except Exception as e:
            logger.error(f"认证过程中出现异常: {e}")
            logger.debug(traceback.format_exc())
            return False

    # --- Data Fetching ---

    async def get_current_model_info(self) -> bool:
        """获取当前模型信息并更新内部状态"""
        if not self.authenticated:
            logger.debug("未认证，跳过获取模型信息")
            return False
            
        response = await self.send_request("CurrentModelRequest")
        if not response or 'data' not in response:
            logger.warning("获取当前模型信息失败")
            return False
            
        model_data = response['data']
        new_model_loaded = model_data.get('modelLoaded', False)
        
        if new_model_loaded:
            new_model_name = model_data.get('modelName', "")
            new_model_id = model_data.get('modelID', "")
            if self.current_model_id != new_model_id:
                 logger.info(f"模型已加载/更改: {new_model_name} (ID: {new_model_id})")
                 self.model_loaded = True
                 self.current_model = new_model_name
                 self.current_model_id = new_model_id
                 # Trigger refresh of model-specific data
                 asyncio.create_task(self.refresh_model_data()) 
            # else: model hasn't changed, no need to log again unless debugging
        elif self.model_loaded: # Model was loaded, now isn't
            logger.info("模型已卸载")
            self.model_loaded = False
            self.current_model = None
            self.current_model_id = None
            # Clear model-specific data
            self.live2d_parameters = []
            self.available_expressions = []
            self.available_hotkeys = []
            self.available_parameters = list(self.tracking_parameters) # Reset available to just tracking params

        return True

    async def get_tracking_parameters(self) -> bool:
        """获取跟踪参数列表（InputParameterListRequest）"""
        if not self.authenticated:
            logger.debug("未认证，跳过获取跟踪参数")
            return False
            
        response = await self.send_request("InputParameterListRequest")
        if not response or 'data' not in response:
             logger.warning("获取跟踪参数列表失败")
             return False

        default_params = response['data'].get('defaultParameters', [])
        custom_params = response['data'].get('customParameters', [])
        self.tracking_parameters = default_params + custom_params
        logger.info(f"获取到 {len(self.tracking_parameters)} 个跟踪参数")
        if not self.tracking_parameters:
            logger.warning("跟踪参数列表为空")
        await self.merge_parameters() # Re-merge after fetching
        return True
    
    async def get_live2d_parameters(self) -> bool:
        """获取Live2D参数列表（Live2DParameterListRequest）"""
        if not self.authenticated or not self.model_loaded:
            logger.debug("未认证或未加载模型，跳过获取Live2D参数")
            return False
            
        response = await self.send_request("Live2DParameterListRequest")
        if not response or 'data' not in response:
            logger.warning("获取Live2D参数列表失败")
            return False
            
        self.live2d_parameters = response['data'].get('parameters', [])
        logger.info(f"获取到 {len(self.live2d_parameters)} 个Live2D参数")
        await self.merge_parameters() # Re-merge after fetching
        return True
    
    async def merge_parameters(self) -> bool:
        """合并跟踪参数和Live2D参数到 available_parameters"""
        logger.debug("合并参数列表...")
        merged_params = []
        merged_names = set()

        # Add tracking parameters first
        for param in self.tracking_parameters:
            if 'name' in param and param['name'] not in merged_names:
                merged_params.append(param)
                merged_names.add(param['name'])
        
        # Add Live2D parameters if not already present by name
        for param in self.live2d_parameters:
            if 'name' in param and param['name'] not in merged_names:
                 # Attempt to add mapping info
                 if param['name'] in self.parameter_mapping:
                     param['mappedToTracking'] = self.parameter_mapping[param['name']]
                 merged_params.append(param)
                 merged_names.add(param['name'])
        
        # Add common/default parameters if they are still missing
        for param in self.common_parameters:
             if param['name'] not in merged_names:
                 merged_params.append(param)
                 merged_names.add(param['name'])

        self.available_parameters = merged_params
        logger.info(f"合并后共有 {len(self.available_parameters)} 个可用参数")
        return True

    async def preload_common_parameters(self):
        """定义一组常见的参数以备后用"""
        logger.info("预加载常见参数定义...")
        self.common_parameters = [
            {"name": "FaceAngleX", "description": "面部水平旋转", "defaultValue": 0, "min": -30, "max": 30},
            {"name": "FaceAngleY", "description": "面部垂直旋转", "defaultValue": 0, "min": -30, "max": 30},
            {"name": "FaceAngleZ", "description": "面部倾斜", "defaultValue": 0, "min": -30, "max": 30},
            {"name": "MouthSmile", "description": "微笑程度", "defaultValue": 0, "min": 0, "max": 1},
            {"name": "MouthOpenY", "description": "嘴巴开合程度", "defaultValue": 0, "min": 0, "max": 1},
            {"name": "EyeOpenLeft", "description": "左眼开合程度", "defaultValue": 1, "min": 0, "max": 1},
            {"name": "EyeOpenRight", "description": "右眼开合程度", "defaultValue": 1, "min": 0, "max": 1},
            {"name": "EyeLeftX", "description": "左眼水平位置", "defaultValue": 0, "min": -1, "max": 1},
            {"name": "EyeLeftY", "description": "左眼垂直位置", "defaultValue": 0, "min": -1, "max": 1},
            {"name": "EyeRightX", "description": "右眼水平位置", "defaultValue": 0, "min": -1, "max": 1},
            {"name": "EyeRightY", "description": "右眼垂直位置", "defaultValue": 0, "min": -1, "max": 1},
            {"name": "BrowLeftY", "description": "左眉毛高度", "defaultValue": 0, "min": -1, "max": 1},
            {"name": "BrowRightY", "description": "右眉毛高度", "defaultValue": 0, "min": -1, "max": 1},
            {"name": "TongueOut", "description": "舌头伸出程度", "defaultValue": 0, "min": 0, "max": 1},
            {"name": "CheekPuff", "description": "脸颊鼓起", "defaultValue": 0, "min": 0, "max": 1},
            {"name": "MouthX", "description": "嘴巴水平位置", "defaultValue": 0, "min": -1, "max": 1}
        ]
        logger.info(f"定义了 {len(self.common_parameters)} 个常见参数")
        await self.merge_parameters() # Merge after defining
        return True
    
    async def get_available_expressions(self) -> bool:
        """获取当前模型可用表情列表"""
        if not self.authenticated or not self.model_loaded:
            logger.debug("未认证或未加载模型，跳过获取表情")
            return False
            
        response = await self.send_request("ExpressionStateRequest", {"details": True})
        if not response or 'data' not in response:
            logger.warning("获取表情列表失败")
            return False
            
        self.available_expressions = response['data'].get('expressions', [])
        logger.info(f"获取到 {len(self.available_expressions)} 个表情")
        return True
    
    async def get_available_hotkeys(self, model_id: Optional[str] = None) -> bool:
        """获取可用热键列表"""
        if not self.authenticated:
            logger.debug("未认证，跳过获取热键")
            return False
        
        # Only fetch if model is loaded, unless specific model_id is given
        if not self.model_loaded and not model_id:
             logger.debug("未加载模型，跳过获取当前模型热键")
             return False

        data = {}
        target_model_id = model_id or self.current_model_id
        if target_model_id:
            data["modelID"] = target_model_id
        else: # If no model is loaded and no specific ID given, request general hotkeys
             logger.info("请求通用热键 (无模型加载)")

        response = await self.send_request("HotkeysInCurrentModelRequest", data)
        if not response or 'data' not in response:
            logger.warning(f"获取模型 {target_model_id or '通用'} 热键列表失败")
            return False
        
        self.available_hotkeys = response['data'].get('availableHotkeys', [])
        logger.info(f"获取到 {len(self.available_hotkeys)} 个模型 {target_model_id or '通用'} 热键")
        return True

    async def get_items_in_scene(self) -> bool:
        """获取场景中的物品列表"""
        if not self.authenticated:
            logger.debug("未认证，跳过获取场景物品")
            return False
            
        # includeAvailableSpots: False - we only care about items currently in the scene
        # includeItemInstancesInScene: True - get instances like 'cat_ears_1'
        # includeAvailableItems: False - don't need the list of items that *can* be added
        response = await self.send_request("ItemListRequest", {
            "includeAvailableSpots": False, 
            "includeItemInstancesInScene": True,
            "includeAvailableItems": False
        })
        if not response or 'data' not in response:
            logger.warning("获取场景物品列表失败")
            return False
            
        self.scene_items = response['data'].get('itemInstancesInScene', [])
        logger.info(f"获取到 {len(self.scene_items)} 个场景物品实例")
        return True

    # --- Control Functions ---

    async def set_parameter_value(self, parameter_id: str, value: float, weight: float = 1.0, mode: str = "set") -> bool:
        """设置单个参数值
        
        Args:
            parameter_id: 参数ID (可以是Live2D或跟踪参数名)
            value: 参数值
            weight: 权重 (0-1), 仅在mode='set'时有效
            mode: "set" 或 "add"
            
        Returns:
            是否成功
        """
        if not self.authenticated:
            logger.error("未认证，无法设置参数值")
            return False
        
        # Map Live2D param to tracking param if possible/needed
        mapped_id = self.parameter_mapping.get(parameter_id, parameter_id)
        if mapped_id != parameter_id:
             logger.debug(f"参数映射: {parameter_id} -> {mapped_id}")
        
        param_data = {
            "id": mapped_id,
            "value": value
        }
        if mode == "set":
            param_data["weight"] = weight # Weight only used in set mode

        data = {
            "faceFound": True, # Assume face found for direct injection
            "mode": mode,
            "parameterValues": [param_data]
        }
        
        response = await self.send_request("InjectParameterDataRequest", data)
        # InjectParameterDataRequest usually returns an empty success response
        # We rely on send_request to have logged API errors if they occurred
        return response is not None # Consider it successful if the request didn't fail at comms level

    async def set_multiple_parameter_values(self, parameters: List[Dict[str, Any]], mode: str = "set") -> bool:
        """设置多个参数值
        
        Args:
            parameters: 参数列表，每个字典包含 'id', 'value', 可选 'weight'
            mode: "set" 或 "add"

        Returns:
            是否成功
        """
        if not self.authenticated:
            logger.error("未认证，无法设置多个参数值")
            return False
        if not parameters:
            logger.warning("参数列表为空，无需发送请求")
            return True

        param_values = []
        for param in parameters:
            if 'id' in param and 'value' in param:
                param_id = param['id']
                value = float(param['value'])
                
                # Map Live2D param to tracking param if possible/needed
                mapped_id = self.parameter_mapping.get(param_id, param_id)
                if mapped_id != param_id:
                    logger.debug(f"参数映射: {param_id} -> {mapped_id}")

                param_entry = {
                    "id": mapped_id,
                    "value": value
                }
                if mode == "set":
                     weight = float(param.get('weight', 1.0))
                     param_entry["weight"] = weight

                param_values.append(param_entry)
            else:
                 logger.warning(f"跳过无效参数项: {param}")

        if not param_values:
            logger.error("没有有效的参数可设置")
            return False
                
        data = {
            "faceFound": True,
            "mode": mode,
            "parameterValues": param_values
        }
        
        response = await self.send_request("InjectParameterDataRequest", data)
        return response is not None

    async def activate_expression(self, expression_file: str, active: bool = True, fade_time: float = 0.5) -> bool:
        """激活或停用表情
        
        Args:
            expression_file: 表情文件名 (应包含.exp3.json)
            active: 是否激活
            fade_time: 淡入淡出时间 (秒)
            
        Returns:
            操作是否成功
        """
        if not self.authenticated:
            logger.error("未认证，无法控制表情")
            return False
        if not self.model_loaded:
            logger.warning("未加载模型，无法控制表情")
            return False
        
        # Basic check for extension, VTS is usually forgiving but good practice
        if not expression_file.lower().endswith(".exp3.json"):
            logger.warning(f"表情文件名 '{expression_file}' 可能缺少 .exp3.json 后缀")
            # Consider adding it automatically if needed: 
            # expression_file += ".exp3.json"
        
        response = await self.send_request("ExpressionActivationRequest", {
            "expressionFile": expression_file,
            "active": active,
            "fadeTime": max(0, fade_time) # Ensure non-negative fade time
        })
        
        # ExpressionActivationRequest returns empty on success, error on failure
        if response is not None:
             # Logged API errors in send_request
             logger.info(f"{'激活' if active else '停用'}表情 '{expression_file}' 请求已发送")
             return True
        else:
             # Error already logged by send_request or comms failure
             logger.error(f"{'激活' if active else '停用'}表情 '{expression_file}' 失败")
             return False

    async def trigger_hotkey(self, hotkey_id_or_name: str) -> bool:
        """触发热键
        
        Args:
            hotkey_id_or_name: 热键的ID或名称
            
        Returns:
            操作是否成功
        """
        if not self.authenticated:
            logger.error("未认证，无法触发热键")
            return False
        
        # Find hotkey ID if name is provided (case-insensitive search)
        target_hotkey_id = None
        if self.available_hotkeys:
             for hotkey in self.available_hotkeys:
                 if hotkey.get('hotkeyID') == hotkey_id_or_name or \
                    hotkey.get('name', '').lower() == hotkey_id_or_name.lower():
                    target_hotkey_id = hotkey.get('hotkeyID')
                    break
        
        if not target_hotkey_id:
             # If not found in cache, try using the provided ID/name directly
             logger.warning(f"热键 '{hotkey_id_or_name}' 未在缓存中找到，尝试直接使用")
             target_hotkey_id = hotkey_id_or_name

        response = await self.send_request("HotkeyTriggerRequest", {
            "hotkeyID": target_hotkey_id
        })
        
        if response and 'data' in response:
             triggered_id = response['data'].get('hotkeyID')
             if triggered_id:
                 logger.info(f"成功触发热键: {triggered_id} (请求: {hotkey_id_or_name})")
                 return True
             else: # Response received but no hotkeyID - likely means hotkey doesn't exist or failed
                 logger.error(f"触发热键失败: {hotkey_id_or_name} (VTS未返回触发ID)")
                 return False
        else:
            # Error already logged by send_request or comms failure
            logger.error(f"触发热键请求失败: {hotkey_id_or_name}")
            return False
            
    async def control_item_animation(self, 
                                     item_instance_id: str, 
                                     play_animation: Optional[bool] = None, 
                                     animation_name: Optional[str] = None, # Added for selecting animation
                                     frame_rate: Optional[float] = None, 
                                     frame: Optional[int] = None, 
                                     auto_stop_frames: Optional[List[int]] = None) -> bool:
        """控制物品动画
        
        Args:
            item_instance_id: 物品实例ID
            play_animation: 是否播放/暂停 (True/False/None=不改变)
            animation_name: 要播放的动画名称 (如果物品有多个动画)
            frame_rate: 帧率 (0.1-120, None=不改变)
            frame: 跳转到指定帧 (None=不改变)
            auto_stop_frames: 自动停止帧列表 (None=不改变, []=清除)
            
        Returns:
            是否成功
        """
        if not self.authenticated:
            logger.error("未认证，无法控制物品动画")
            return False
            
        data: Dict[str, Any] = {
            "itemInstanceID": item_instance_id,
        }
        
        # Control flags - VTS requires these to know what to change
        set_play_state = False
        set_stop_frames = False
        set_animation = False # Added flag for animation name

        if play_animation is not None:
            data["animationPlayState"] = play_animation
            set_play_state = True
        
        if animation_name is not None:
             data["animationToPlay"] = animation_name
             set_animation = True # Need to tell VTS to set the animation
        
        if frame_rate is not None:
            data["framerate"] = max(0.1, min(120, frame_rate)) # Clamp value
        
        if frame is not None:
            data["frame"] = max(0, frame) # Ensure non-negative frame

        if auto_stop_frames is not None: # Allow empty list to clear
            data["autoStopFrames"] = auto_stop_frames
            set_stop_frames = True
            
        # Only include control flags if corresponding value was set
        if set_play_state: data["setAnimationPlayState"] = True
        if set_stop_frames: data["setAutoStopFrames"] = True
        if set_animation: data["setAnimationToPlay"] = True # Added flag
        
        # Don't send request if nothing is being changed
        if len(data) <= 1: # Only contains itemInstanceID
             logger.info("没有指定动画控制更改，跳过请求")
             return True

        response = await self.send_request("ItemAnimationControlRequest", data)
        
        # ItemAnimationControl returns empty on success, error on failure
        if response is not None:
            logger.info(f"物品动画控制请求已发送: {item_instance_id}")
            return True
        else:
            # Error already logged by send_request or comms failure
            logger.error(f"物品动画控制请求失败: {item_instance_id}")
            return False
            
    async def play_item_animation(self, item_instance_id: str, animation_name: Optional[str] = None, frame_rate: float = 30.0) -> bool:
        """播放物品动画"""
        return await self.control_item_animation(
            item_instance_id=item_instance_id,
            play_animation=True,
            animation_name=animation_name,
            frame_rate=frame_rate
        )
    
    async def stop_item_animation(self, item_instance_id: str) -> bool:
        """停止物品动画"""
        return await self.control_item_animation(
            item_instance_id=item_instance_id,
            play_animation=False
        )
        
    async def _auto_stop_expression_animation(self, animation_file: str, delay: float):
        """后台任务：延迟后停止表情动画"""
        await asyncio.sleep(delay)
        logger.info(f"自动停止表情动画: {animation_file} (延迟: {delay}s)")
        await self.activate_expression(animation_file, False, 0.5) # Use default fade out

    # --- Initialization and Main Loop ---

    async def initialize(self) -> bool:
        """初始化插件：连接、认证、加载初始数据"""
        logger.info("插件初始化开始...")
        
        # 0. Preload common parameter definitions
        await self.preload_common_parameters()
        
        # 1. Connect
        if not await self.connect():
            logger.error("初始化失败：无法连接到VTubeStudio")
            return False
            
        # 2. Authenticate
        auth_success = await self.authenticate()
        if not auth_success:
            logger.warning("认证未成功，插件功能受限。请在VTubeStudio中授权。")
            # Continue initialization, but some fetches might fail
        else:
            logger.info("认证成功")
        
        # 3. Fetch initial data if authenticated
        if self.authenticated:
            await self.refresh_all_data()
        else:
            # Fetch data that doesn't strictly require authentication? (e.g., maybe tracking params?)
            # await self.get_tracking_parameters() # Decide if this is useful when not authenticated
            pass

        logger.info("插件初始化完成")
        return True

    async def refresh_all_data(self):
         """刷新所有需要认证的数据"""
         logger.info("正在刷新所有数据...")
         if not self.authenticated:
             logger.warning("未认证，无法刷新数据")
             return

         await self.get_current_model_info() # This triggers refresh_model_data if model changes
         await self.get_tracking_parameters() # Always refresh tracking params
         await self.get_items_in_scene() # Refresh scene items
         # Model specific data is refreshed via get_current_model_info -> refresh_model_data
         # Explicitly call merge params in case tracking params changed but model didn't
         await self.merge_parameters() 
         logger.info("数据刷新完成")

    async def refresh_model_data(self):
         """刷新与当前模型相关的数据"""
         logger.info(f"正在刷新模型 '{self.current_model}' 的数据...")
         if not self.authenticated or not self.model_loaded:
             logger.warning("未认证或未加载模型，无法刷新模型数据")
             return
             
         await self.get_live2d_parameters()
         await self.get_available_expressions()
         await self.get_available_hotkeys()
         await self.merge_parameters() # Ensure merging after fetching model params
         logger.info(f"模型 '{self.current_model}' 数据刷新完成")

    async def run_periodic_refresh(self, interval_seconds: int = 30):
        """后台任务：定期刷新数据和检查连接"""
        logger.info(f"启动定期刷新任务 (间隔: {interval_seconds}秒)")
        while True:
            try:
                await asyncio.sleep(interval_seconds)
                logger.debug("执行定期刷新...")
                
                # Check connection first
                connection_ok = await self.check_connection()
                if not connection_ok:
                    logger.warning("检测到WebSocket连接断开，尝试重新连接并认证...")
                    if await self.connect():
                         await self.authenticate()
                    else:
                         logger.error("重新连接失败，将在下一个周期重试")
                         continue # Skip refresh if connection failed

                # Refresh data if authenticated
                if self.authenticated:
                    await self.refresh_all_data()
                else:
                     # Maybe attempt re-authentication periodically?
                     logger.debug("未认证，跳过定期数据刷新")
                     # await self.authenticate() # Uncomment to try re-auth periodically

            except asyncio.CancelledError:
                 logger.info("定期刷新任务已取消")
                 break
            except Exception as e:
                logger.error(f"定期刷新任务中出错: {e}")
                logger.debug(traceback.format_exc())
                # Wait a bit longer after an error before retrying
                await asyncio.sleep(interval_seconds)

    # --- API Server ---

    async def start_api_server(self):
        """启动 aiohttp API 服务器"""
        app = web.Application()
        
        # Add routes
        app.router.add_get('/', self.handle_root)
        app.router.add_get('/status', self.handle_get_status)
        # Parameters
        app.router.add_get('/parameters', self.handle_get_parameters)
        app.router.add_post('/parameter', self.handle_set_parameter) # Single param
        app.router.add_post('/parameters', self.handle_set_parameters) # Multiple params
        # Expressions
        app.router.add_get('/expressions', self.handle_get_expressions)
        app.router.add_post('/expression', self.handle_activate_expression) # Activate/deactivate
        # Hotkeys
        app.router.add_get('/hotkeys', self.handle_get_hotkeys)
        app.router.add_post('/hotkey', self.handle_trigger_hotkey)
        # Items
        app.router.add_get('/items', self.handle_get_items)
        app.router.add_post('/item/animation/control', self.handle_control_item_animation)
        app.router.add_post('/item/animation/play', self.handle_play_item_animation)
        app.router.add_post('/item/animation/stop', self.handle_stop_item_animation)
        # Expression-based Animation (Simplified)
        app.router.add_post('/animation/play', self.handle_play_expression_animation) # Plays an expression
        app.router.add_post('/animation/stop', self.handle_stop_expression_animation) # Stops an expression

        # CORS setup
        app.router.add_options('/{tail:.*}', self._preflight_handler)
        app.on_response_prepare.append(self._set_cors_headers)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.api_port)
        
        try:
            await site.start()
            logger.info(f"API服务器已启动，监听地址: http://0.0.0.0:{self.api_port}")
            
            # Start periodic refresh task
            refresh_task = asyncio.create_task(self.run_periodic_refresh())

            # Keep server running until interrupted
            await asyncio.Event().wait() # Keep running indefinitely

        except OSError as e:
             logger.error(f"启动API服务器失败 (端口 {self.api_port} 可能已被占用): {e}")
        except Exception as e:
             logger.error(f"API服务器运行时出错: {e}")
             logger.debug(traceback.format_exc())
        finally:
            logger.info("正在关闭API服务器...")
            if 'refresh_task' in locals() and not refresh_task.done():
                refresh_task.cancel()
                await asyncio.wait([refresh_task], timeout=5) # Wait briefly for cleanup
            await runner.cleanup()
            logger.info("API服务器已关闭")

    # --- API Handlers ---

    async def handle_root(self, request):
        """根路径，显示插件基本信息"""
        return web.json_response({
            "pluginName": self.plugin_name,
            "pluginDeveloper": self.plugin_developer,
            "status": {
                 "connected_to_vts": self.ws_connected,
                 "authenticated": self.authenticated,
                 "model_loaded": self.model_loaded,
                 "current_model": self.current_model,
            }
        })

    async def handle_get_status(self, request):
        """获取详细状态"""
        return web.json_response({
            "connected_to_vts": self.ws_connected,
            "authenticated": self.authenticated,
            "model_loaded": self.model_loaded,
            "current_model": self.current_model,
            "current_model_id": self.current_model_id,
            "parameter_count": len(self.available_parameters),
            "expression_count": len(self.available_expressions),
            "hotkey_count": len(self.available_hotkeys),
            "scene_item_count": len(self.scene_items),
        })

    async def handle_get_parameters(self, request):
        """获取可用参数列表"""
        # Optionally force refresh if query param exists? e.g., /parameters?refresh=true
        # await self.get_tracking_parameters()
        # if self.model_loaded: await self.get_live2d_parameters()
        # await self.merge_parameters()
        return web.json_response({"parameters": self.available_parameters})
    
    async def handle_get_expressions(self, request):
        """获取可用表情列表"""
        # Optionally force refresh
        # if self.model_loaded: await self.get_available_expressions()
        return web.json_response({"expressions": self.available_expressions})
    
    async def handle_get_hotkeys(self, request):
        """获取可用热键列表"""
        # Optionally force refresh
        # model_id = request.query.get("model_id")
        # await self.get_available_hotkeys(model_id)
        return web.json_response({"hotkeys": self.available_hotkeys})

    async def handle_get_items(self, request):
        """获取场景物品列表"""
        # Optionally force refresh
        # await self.get_items_in_scene()
        return web.json_response({"items": self.scene_items})

    async def handle_set_parameter(self, request):
        """处理设置单个参数请求"""
        try:
            data = await request.json()
            param_id = data.get('id')
            value = data.get('value')
            weight = data.get('weight', 1.0)
            mode = data.get('mode', 'set').lower()

            if param_id is None or value is None:
                return web.json_response({"error": "缺少 'id' 或 'value' 参数"}, status=400)
            if mode not in ['set', 'add']:
                 return web.json_response({"error": "无效的 'mode'，必须是 'set' 或 'add'"}, status=400)
                
            success = await self.set_parameter_value(param_id, float(value), float(weight), mode)
            return web.json_response({"success": success})
        except ValueError:
             return web.json_response({"error": "'value' 或 'weight' 必须是数字"}, status=400)
        except Exception as e:
            logger.error(f"处理设置参数请求时出错: {e}", exc_info=True)
            return web.json_response({"error": "内部服务器错误"}, status=500)
            
    async def handle_set_parameters(self, request):
        """处理设置多个参数请求"""
        try:
            data = await request.json()
            parameters = data.get('parameters')
            mode = data.get('mode', 'set').lower()

            if not isinstance(parameters, list):
                return web.json_response({"error": "'parameters' 必须是一个列表"}, status=400)
            if mode not in ['set', 'add']:
                 return web.json_response({"error": "无效的 'mode'，必须是 'set' 或 'add'"}, status=400)

            success = await self.set_multiple_parameter_values(parameters, mode)
            return web.json_response({"success": success})
        except Exception as e:
            logger.error(f"处理设置多个参数请求时出错: {e}", exc_info=True)
            return web.json_response({"error": "内部服务器错误"}, status=500)

    async def handle_activate_expression(self, request):
        """处理激活/停用表情请求"""
        try:
            data = await request.json()
            expression_file = data.get("file")
            active = data.get("active", True) # Default to activate
            fade_time = data.get("fadeTime", 0.5)
            
            if not expression_file:
                return web.json_response({"error": "缺少 'file' (表情文件名) 参数"}, status=400)
            
            success = await self.activate_expression(expression_file, bool(active), float(fade_time))
            return web.json_response({"success": success})
        except ValueError:
             return web.json_response({"error": "'fadeTime' 必须是数字, 'active' 必须是布尔值"}, status=400)
        except Exception as e:
            logger.error(f"处理激活表情请求时出错: {e}", exc_info=True)
            return web.json_response({"error": "内部服务器错误"}, status=500)

    async def handle_trigger_hotkey(self, request):
        """处理触发热键请求"""
        try:
            data = await request.json()
            hotkey_id = data.get("id")
            
            if not hotkey_id:
                return web.json_response({"error": "缺少 'id' (热键ID或名称) 参数"}, status=400)
            
            success = await self.trigger_hotkey(str(hotkey_id))
            return web.json_response({"success": success})
        except Exception as e:
            logger.error(f"处理触发热键请求时出错: {e}", exc_info=True)
            return web.json_response({"error": "内部服务器错误"}, status=500)
            
    async def handle_control_item_animation(self, request):
        """处理控制物品动画请求"""
        try:
            data = await request.json()
            item_instance_id = data.get('itemInstanceID')
            play_animation = data.get('playAnimation') # Can be None
            animation_name = data.get('animationName') # Can be None
            frame_rate = data.get('frameRate')         # Can be None
            frame = data.get('frame')             # Can be None
            auto_stop_frames = data.get('autoStopFrames') # Can be None or []

            if not item_instance_id:
                return web.json_response({"error": "缺少 'itemInstanceID'"}, status=400)
            
            # Type validation/conversion
            if frame_rate is not None: frame_rate = float(frame_rate)
            if frame is not None: frame = int(frame)
            if play_animation is not None: play_animation = bool(play_animation)
            if auto_stop_frames is not None and not isinstance(auto_stop_frames, list):
                 return web.json_response({"error": "'autoStopFrames' 必须是列表或null"}, status=400)

            success = await self.control_item_animation(
                item_instance_id=item_instance_id,
                play_animation=play_animation,
                animation_name=animation_name,
                frame_rate=frame_rate,
                frame=frame,
                auto_stop_frames=auto_stop_frames
            )
            return web.json_response({"success": success})
        except ValueError:
             return web.json_response({"error": "类型转换错误 (确保数字是数字，布尔是布尔)"}, status=400)
        except Exception as e:
            logger.error(f"处理控制物品动画请求时出错: {e}", exc_info=True)
            return web.json_response({"error": "内部服务器错误"}, status=500)
            
    async def handle_play_item_animation(self, request):
        """处理播放物品动画快捷方式请求"""
        try:
            data = await request.json()
            item_instance_id = data.get('itemInstanceID')
            animation_name = data.get('animationName') # Optional specific animation
            frame_rate = data.get('frameRate', 30.0)

            if not item_instance_id:
                return web.json_response({"error": "缺少 'itemInstanceID'"}, status=400)

            success = await self.play_item_animation(item_instance_id, animation_name, float(frame_rate))
            return web.json_response({"success": success})
        except ValueError:
             return web.json_response({"error": "'frameRate' 必须是数字"}, status=400)
        except Exception as e:
            logger.error(f"处理播放物品动画请求时出错: {e}", exc_info=True)
            return web.json_response({"error": "内部服务器错误"}, status=500)

    async def handle_stop_item_animation(self, request):
        """处理停止物品动画快捷方式请求"""
        try:
            data = await request.json()
            item_instance_id = data.get('itemInstanceID')

            if not item_instance_id:
                return web.json_response({"error": "缺少 'itemInstanceID'"}, status=400)

            success = await self.stop_item_animation(item_instance_id)
            return web.json_response({"success": success})
        except Exception as e:
            logger.error(f"处理停止物品动画请求时出错: {e}", exc_info=True)
            return web.json_response({"error": "内部服务器错误"}, status=500)
            
    async def handle_play_expression_animation(self, request):
        """处理播放动画请求 (通过激活表情)"""
        try:
            data = await request.json()
            animation_file = data.get("file")  # 表情文件名
            fade_time = data.get("fadeTime", 0.5)
            auto_stop = data.get("autoStop", False) # Whether to stop automatically
            stop_after = data.get("stopAfter", 0)  # Delay in seconds before stopping

            if not animation_file:
                return web.json_response({"error": "缺少 'file' (表情文件名) 参数"}, status=400)
            
            success = await self.activate_expression(animation_file, True, float(fade_time))
            
            if success and bool(auto_stop) and float(stop_after) > 0:
                # Schedule the stop task
                asyncio.create_task(self._auto_stop_expression_animation(animation_file, float(stop_after)))
                logger.info(f"已计划在 {stop_after} 秒后自动停止表情 '{animation_file}'")

            return web.json_response({"success": success})
        except ValueError:
             return web.json_response({"error": "类型转换错误 ('fadeTime', 'stopAfter' 应为数字, 'autoStop' 应为布尔值)"}, status=400)
        except Exception as e:
            logger.error(f"处理播放表情动画请求时出错: {e}", exc_info=True)
            return web.json_response({"error": "内部服务器错误"}, status=500)

    async def handle_stop_expression_animation(self, request):
        """处理停止动画请求 (通过停用表情)"""
        try:
            data = await request.json()
            animation_file = data.get("file")  # 表情文件名
            fade_time = data.get("fadeTime", 0.5)
            
            if not animation_file:
                return web.json_response({"error": "缺少 'file' (表情文件名) 参数"}, status=400)
            
            success = await self.activate_expression(animation_file, False, float(fade_time))
            return web.json_response({"success": success})
        except ValueError:
             return web.json_response({"error": "'fadeTime' 必须是数字"}, status=400)
        except Exception as e:
            logger.error(f"处理停止表情动画请求时出错: {e}", exc_info=True)
            return web.json_response({"error": "内部服务器错误"}, status=500)

    # --- CORS Handlers ---
    
    async def _preflight_handler(self, request):
        """处理 CORS 预检请求 (OPTIONS)"""
        headers = {
            'Access-Control-Allow-Origin': '*', # Allow all origins for simplicity, restrict if needed
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization', # Add headers your frontend might send
            'Access-Control-Max-Age': '86400' # Cache preflight response for 1 day
        }
        return web.Response(headers=headers)

    async def _set_cors_headers(self, request, response):
        """为所有响应添加 CORS 头"""
        # Be careful not to overwrite existing headers needed by aiohttp
        response.headers['Access-Control-Allow-Origin'] = '*'
        # Optionally add other CORS headers if needed, like Allow-Credentials


async def main():
    """主函数：解析参数并启动插件"""
    parser = argparse.ArgumentParser(description='VTube Studio 统一控制插件')
    parser.add_argument('--ws-url', type=str, default='ws://localhost:8001', help='VTube Studio WebSocket URL')
    parser.add_argument('--api-port', type=int, default=8080, help='API 服务器监听端口')
    parser.add_argument('--plugin-name', type=str, default='VTS Unified Plugin', help='在 VTS 中显示的插件名称')
    parser.add_argument('--plugin-dev', type=str, default='Manus AI', help='在 VTS 中显示的插件开发者')
    parser.add_argument('--debug', action='store_true', help='启用详细调试日志')
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('websockets').setLevel(logging.DEBUG) # Enable websockets debug logs
        logging.getLogger('aiohttp').setLevel(logging.DEBUG)   # Enable aiohttp debug logs
    else:
         # Keep external libraries less verbose in info mode
         logging.getLogger('websockets').setLevel(logging.WARNING)
         logging.getLogger('aiohttp').setLevel(logging.WARNING)
         
    
    plugin = VTSUnifiedPlugin(
        plugin_name=args.plugin_name,
        plugin_developer=args.plugin_dev,
        vts_ws_url=args.ws_url,
        api_port=args.api_port
    )
    
    try:
        # 初始化插件（连接和认证）
        init_success = await plugin.initialize()
        if not init_success and not plugin.authenticated:
             logger.warning("插件初始化部分失败（可能未认证），API服务器仍将启动，但功能受限。")
        elif not init_success:
             logger.error("插件初始化失败，无法启动 API 服务器。")
             return # Exit if core initialization failed badly

        # 启动API服务器并保持运行
        await plugin.start_api_server()
        
    except KeyboardInterrupt:
        logger.info("接收到中断信号 (Ctrl+C)，正在关闭...")
    except Exception as e:
         logger.critical(f"发生未处理的顶层异常: {e}", exc_info=True)
    finally:
        logger.info("正在清理资源...")
        if plugin.ws_connected:
            await plugin.disconnect()
        logger.info("插件已退出。")

if __name__ == "__main__":
    # For Windows asyncio policy fix if needed:
    # if os.name == 'nt':
    #     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
         asyncio.run(main())
    except KeyboardInterrupt:
         # Catch interrupt during asyncio.run() if it happens before main loop
         logger.info("程序被中断。")
