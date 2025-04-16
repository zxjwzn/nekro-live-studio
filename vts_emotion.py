import asyncio
import json
import logging
import websockets
import aiohttp
from aiohttp import web
import os
import time
import uuid
from typing import List, Dict, Any, Optional, Union

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - VTS_Model_Motion - %(levelname)s - %(message)s'
)
logger = logging.getLogger('VTS_Model_Motion')

class VTSModelMotionPlugin:
    """VTubeStudio模型动画控制插件"""
    
    def __init__(self, plugin_name: str = "VTS Model Motion Plugin", 
                 plugin_developer: str = "Manus AI", 
                 ws_url: str = "ws://localhost:8001",
                 api_port: int = 8080):
        """初始化插件
        
        Args:
            plugin_name: 插件名称
            plugin_developer: 插件开发者
            ws_url: VTubeStudio WebSocket URL
            api_port: API服务器端口
        """
        self.plugin_name = plugin_name
        self.plugin_developer = plugin_developer
        self.ws_url = ws_url
        self.api_port = api_port
        
        # WebSocket连接
        self.ws = None
        self.ws_connected = False
        self.authenticated = False
        self.auth_token = None
        
        # 模型信息
        self.model_loaded = False
        self.current_model = None
        self.model_id = None
        
        # 表情和热键信息
        self.available_expressions = []
        self.available_hotkeys = []
        
        # 请求ID计数器
        self.request_counter = 0
        
    async def connect(self) -> bool:
        """连接到VTubeStudio WebSocket服务器"""
        try:
            self.ws = await websockets.connect(self.ws_url)
            logger.info(f"已连接到VTubeStudio: {self.ws_url}")
            self.ws_connected = True
            return True
        except Exception as e:
            logger.error(f"连接VTubeStudio失败: {e}")
            self.ws_connected = False
            return False
    
    async def disconnect(self) -> bool:
        """断开与VTubeStudio的连接"""
        if self.ws:
            await self.ws.close()
            self.ws = None
            self.ws_connected = False
            self.authenticated = False
            logger.info("已断开与VTubeStudio的连接")
            return True
        return False
    
    async def check_connection(self) -> bool:
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
    
    async def send_request(self, message_type: str, data: Dict) -> Dict:
        """向VTubeStudio发送请求
        
        Args:
            message_type: 请求类型
            data: 请求数据
            
        Returns:
            响应数据
        """
        if not self.ws_connected:
            logger.error("未连接到VTubeStudio，无法发送请求")
            return
        
        self.request_counter += 1
        request_id = f"req_{self.request_counter}_{int(time.time())}"
        
        request = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": request_id,
            "messageType": message_type
        }
        
        if data:
            request["data"] = data
        
        try:
            await self.ws.send(json.dumps(request))
            response = await self.ws.recv()
            response_data = json.loads(response)
            
            # 检查响应是否成功
            if response_data.get("messageType") == message_type + "Response":
                return response_data
            else:
                error_message = response_data.get("data", {}).get("errorMessage", "未知错误")
                logger.error(f"请求失败: {error_message}")
                return None
        except Exception as e:
            logger.error(f"发送请求时出错: {e}")
            return None
    
    async def authenticate(self) -> bool:
        """向VTubeStudio进行身份验证"""
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
            logger.info("请求认证令牌...")
            token_response = await self.send_request("AuthenticationTokenRequest", {
                "pluginName": self.plugin_name,
                "pluginDeveloper": self.plugin_developer
            })
            
            if not token_response:
                logger.error("请求认证令牌失败")
                return False
            
            # 获取认证令牌
            auth_token = token_response.get("data", {}).get("authenticationToken")
            if not auth_token:
                logger.error("未收到认证令牌")
                return False
            
            self.auth_token = auth_token
            logger.info(f"收到认证令牌: {auth_token}")
            
            # 等待用户在VTubeStudio中接受认证请求
            logger.info("等待用户在VTubeStudio中接受认证请求...")
            await asyncio.sleep(2)  # 给用户一些时间接受认证请求
            
            # 第二步：使用令牌进行认证
            logger.info("使用令牌进行认证...")
            auth_response = await self.send_request("AuthenticationRequest", {
                "pluginName": self.plugin_name,
                "pluginDeveloper": self.plugin_developer,
                "authenticationToken": auth_token
            })
            
            if not auth_response:
                logger.error("认证失败")
                return False
            
            # 检查认证是否成功
            authenticated = auth_response.get("data", {}).get("authenticated", False)
            if authenticated:
                logger.info("认证成功")
                self.authenticated = True
                return True
            else:
                reason = auth_response.get("data", {}).get("reason", "未知原因")
                logger.error(f"认证失败: {reason}")
                return False
                
        except Exception as e:
            logger.error(f"认证过程中出错: {e}")
            return False
    
    async def get_current_model_info(self) -> Dict:
        """获取当前加载的模型信息"""
        if not self.authenticated:
            logger.error("未认证，无法获取模型信息")
            return None
        
        response = await self.send_request("CurrentModelRequest")
        if not response:
            return None
        
        model_data = response.get("data", {})
        self.model_loaded = model_data.get("modelLoaded", False)
        self.current_model = model_data.get("modelName")
        self.model_id = model_data.get("modelID")
        
        logger.info(f"当前模型: {self.current_model if self.model_loaded else '无'}")
        return model_data
    
    async def get_available_expressions(self) -> List[Dict]:
        """获取当前模型的可用表情列表"""
        if not self.authenticated:
            logger.error("未认证，无法获取表情列表")
            return []
        
        if not self.model_loaded:
            logger.warning("未加载模型，无法获取表情列表")
            return []
        
        response = await self.send_request("ExpressionStateRequest", {
            "details": True
        })
        
        if not response:
            return []
        
        expressions = response.get("data", {}).get("expressions", [])
        self.available_expressions = expressions
        logger.info(f"获取到 {len(expressions)} 个表情")
        return expressions
    
    async def get_available_hotkeys(self, model_id: str = None) -> List[Dict]:
        """获取可用的热键列表
        
        Args:
            model_id: 模型ID，如果为None则获取当前模型的热键
            
        Returns:
            热键列表
        """
        if not self.authenticated:
            logger.error("未认证，无法获取热键列表")
            return []
        
        data = {}
        if model_id:
            data["modelID"] = model_id
        
        response = await self.send_request("HotkeysInCurrentModelRequest", data)
        if not response:
            return []
        
        hotkeys = response.get("data", {}).get("availableHotkeys", [])
        self.available_hotkeys = hotkeys
        logger.info(f"获取到 {len(hotkeys)} 个热键")
        return hotkeys
    
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
    
    async def trigger_hotkey(self, hotkey_id: str) -> bool:
        """触发热键
        
        Args:
            hotkey_id: 热键ID或名称
            
        Returns:
            操作是否成功
        """
        if not self.authenticated:
            logger.error("未认证，无法触发热键")
            return False
        
        response = await self.send_request("HotkeyTriggerRequest", {
            "hotkeyID": hotkey_id
        })
        
        if not response:
            return False
        
        executed_hotkey = response.get("data", {}).get("hotkeyID")
        if executed_hotkey:
            logger.info(f"触发热键成功: {executed_hotkey}")
            return True
        else:
            logger.error(f"触发热键失败: {hotkey_id}")
            return False
    
    async def initialize(self) -> bool:
        """初始化插件"""
        # 连接到VTubeStudio
        if not await self.connect():
            logger.error("连接VTubeStudio失败")
            return False
            
        # 认证
        auth_success = await self.authenticate()
        if not auth_success:
            logger.warning("认证未成功，部分功能可能不可用")
        else:
            logger.info("认证成功")
        
        # 获取当前模型信息
        await self.get_current_model_info()
        
        # 如果有模型加载，获取可用表情和热键
        if self.model_loaded:
            await self.get_available_expressions()
            await self.get_available_hotkeys()
            
        return True
    
    # API服务器处理函数
    async def handle_get_status(self, request):
        """处理获取状态请求"""
        status = {
            "connected": self.ws_connected,
            "authenticated": self.authenticated,
            "model_loaded": self.model_loaded,
            "current_model": self.current_model,
            "model_id": self.model_id
        }
        return web.json_response(status)
    
    async def handle_get_expressions(self, request):
        """处理获取表情列表请求"""
        await self.get_available_expressions()
        return web.json_response({"expressions": self.available_expressions})
    
    async def handle_get_hotkeys(self, request):
        """处理获取热键列表请求"""
        model_id = request.query.get("model_id")
        hotkeys = await self.get_available_hotkeys(model_id)
        return web.json_response({"hotkeys": hotkeys})
    
    async def handle_activate_expression(self, request):
        """处理激活表情请求"""
        try:
            data = await request.json()
            expression_file = data.get("file")
            active = data.get("active", True)
            fade_time = data.get("fadeTime", 0.5)
            
            if not expression_file:
                return web.json_response({"error": "缺少表情文件名"}, status=400)
            
            success = await self.activate_expression(expression_file, active, fade_time)
            return web.json_response({"success": success})
        except Exception as e:
            logger.error(f"处理激活表情请求时出错: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def handle_trigger_hotkey(self, request):
        """处理触发热键请求"""
        try:
            data = await request.json()
            hotkey_id = data.get("id")
            
            if not hotkey_id:
                return web.json_response({"error": "缺少热键ID"}, status=400)
            
            success = await self.trigger_hotkey(hotkey_id)
            return web.json_response({"success": success})
        except Exception as e:
            logger.error(f"处理触发热键请求时出错: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
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
    
    async def _auto_stop_animation(self, animation_file: str, delay: float):
        """自动停止动画
        
        Args:
            animation_file: 表情文件名
            delay: 延迟时间（秒）
        """
        await asyncio.sleep(delay)
        await self.activate_expression(animation_file, False, 0.5)
        logger.info(f"自动停止动画: {animation_file}")
    
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
    
    async def start_api_server(self):
        """启动API服务器"""
        app = web.Application()
        
        # 路由
        app.router.add_get('/', self.handle_get_status)
        app.router.add_get('/status', self.handle_get_status)
        app.router.add_get('/expressions', self.handle_get_expressions)
        app.router.add_get('/hotkeys', self.handle_get_hotkeys)
        app.router.add_post('/expression', self.handle_activate_expression)
        app.router.add_post('/hotkey', self.handle_trigger_hotkey)
        app.router.add_post('/animation/play', self.handle_play_animation)
        app.router.add_post('/animation/stop', self.handle_stop_animation)
        
        # CORS设置
        app.router.add_options('/{tail:.*}', self._preflight_handler)
        app.on_response_prepare.append(self._set_cors_headers)
        
        # 启动服务器
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.api_port)
        await site.start()
        logger.info(f"API服务器已启动，监听端口: {self.api_port}")
        
        # 保持服务器运行并定期刷新状态
        try:
            while True:
                await asyncio.sleep(30)  # 每30秒检查一次
                
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
                    if self.model_loaded:
                        await self.get_available_expressions()
                        await self.get_available_hotkeys()
                        
        except KeyboardInterrupt:
            logger.info("接收到中断信号，正在关闭...")
        finally:
            # 清理资源
            if self.ws:
                await self.ws.close()
            await runner.cleanup()
    
    async def _preflight_handler(self, request):
        """处理CORS预检请求"""
        return web.Response()
    
    async def _set_cors_headers(self, request, response):
        """设置CORS头"""
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'

async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='VTubeStudio模型动画控制插件')
    parser.add_argument('--ws-url', type=str, default='ws://localhost:8001', help='VTubeStudio WebSocket URL')
    parser.add_argument('--api-port', type=int, default=8080, help='API服务器端口')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    plugin = VTSModelMotionPlugin(
        ws_url=args.ws_url,
        api_port=args.api_port
    )
    
    # 初始化插件
    await plugin.initialize()
    
    # 启动API服务器
    await plugin.start_api_server()

if __name__ == "__main__":
    asyncio.run(main())
