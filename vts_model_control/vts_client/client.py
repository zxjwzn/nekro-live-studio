"""
VTubeStudio 客户端
"""

import asyncio
import json
import logging
import traceback
import uuid
from typing import Any, Callable, Dict, Optional, Coroutine

import websockets

from .exceptions import AuthenticationError, ConnectionError, APIError, ResponseError
from .models import (
    VTSRequest,
    VTSResponse,
    APIStateRequest,
    AuthenticationTokenRequest,
    AuthenticationRequest,
    EventSubscriptionRequest,
    EventSubscriptionResponse,  # 添加导入
)

# 设置日志
logger = logging.getLogger("vts_client")


class VTSClient:
    """VTubeStudio WebSocket 客户端"""

    def __init__(
        self,
        plugin_name: str,
        plugin_developer: str,
        plugin_icon: Optional[str] = None,
        endpoint: str = "ws://localhost:8001",
    ):
        """
        初始化 VTubeStudio 客户端

        Args:
            plugin_name: 插件名称
            plugin_developer: 插件开发者
            plugin_icon: 插件图标 (base64编码的图片)
            endpoint: VTubeStudio WebSocket 端点
        """
        self.plugin_name = plugin_name
        self.plugin_developer = plugin_developer
        self.plugin_icon = plugin_icon
        self.endpoint = endpoint
        self.websocket = None
        self.authentication_token = None
        self.is_authenticated = False
        self.plugin_id = ""
        self.pending_requests = {}
        self.event_callbacks = {}
        self._recv_task = None
        self._message_queue = asyncio.Queue()
        self._connected = False

    async def connect(self) -> None:
        """连接到 VTubeStudio"""
        logger.info(f"正在连接到VTubeStudio: {self.endpoint}")
        try:
            self.websocket = await websockets.connect(self.endpoint)
            logger.info("已连接到VTubeStudio")
            self._connected = True
            self._recv_task = asyncio.create_task(self._receive_messages())
        except Exception as e:
            logger.error(f"连接到VTubeStudio失败: {str(e)}")
            logger.error(traceback.format_exc())
            raise ConnectionError(f"连接到VTubeStudio失败: {str(e)}")

    async def disconnect(self) -> None:
        """断开与 VTubeStudio 的连接"""
        self._connected = False

        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass
            self._recv_task = None

        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            self.is_authenticated = False
            logger.info("已断开与VTubeStudio的连接")

    async def authenticate(self) -> bool:
        """
        执行认证流程
        1. 检查当前API状态
        2. 请求认证令牌
        3. 使用令牌进行认证

        Returns:
            bool: 认证是否成功
        """
        if not self.websocket or not self._connected:
            raise ConnectionError("未连接到VTubeStudio")

        try:
            # 步骤0: 检查API状态
            logger.info("正在获取API状态...")
            api_state_request = APIStateRequest()

            api_state_response = await self.send_request(api_state_request)

            is_authenticated = api_state_response.data.get(
                "currentSessionAuthenticated", False
            )
            logger.info(f"当前认证状态: {is_authenticated}")

            # 如果已经认证，则不需要再次认证
            if is_authenticated:
                self.is_authenticated = True
                logger.info("已经认证，无需再次认证")
                return True

            # 步骤1: 请求认证令牌
            logger.info("正在请求认证令牌...")
            # 使用模型类替代原始字典
            token_request = AuthenticationTokenRequest(
                plugin_name=self.plugin_name,
                plugin_developer=self.plugin_developer,
                plugin_icon=self.plugin_icon,
            )

            token_response = await self.send_request(token_request)

            if token_response.error:
                error_msg = token_response.data.get("message", "未知错误")
                logger.error(f"获取认证令牌失败: {error_msg}")
                raise AuthenticationError(f"获取认证令牌失败: {error_msg}")

            if "authenticationToken" not in token_response.data:
                logger.error("认证令牌响应格式错误")
                raise AuthenticationError("认证令牌响应格式错误")

            self.authentication_token = token_response.data["authenticationToken"]
            logger.info(f"获取到认证令牌: {self.authentication_token}")

            # 步骤2: 使用令牌进行认证
            logger.info("正在使用令牌进行认证...")
            # 使用模型类替代原始字典
            auth_request = AuthenticationRequest(
                plugin_name=self.plugin_name,
                plugin_developer=self.plugin_developer,
                authentication_token=self.authentication_token,
                plugin_icon=self.plugin_icon,
            )

            auth_response = await self.send_request(auth_request)

            if auth_response.error:
                error_msg = auth_response.data.get("message", "未知错误")
                logger.error(f"认证失败: {error_msg}")
                raise AuthenticationError(f"认证失败: {error_msg}")

            authenticated = auth_response.data.get("authenticated", False)
            if not authenticated:
                reason = auth_response.data.get("reason", "未知原因")
                logger.error(f"认证失败: {reason}")
                raise AuthenticationError(f"认证失败: {reason}")

            self.is_authenticated = True
            self.plugin_id = auth_response.data.get("pluginID", "")
            logger.info(f"认证成功，插件ID: {self.plugin_id}")
            return True

        except AuthenticationError as e:
            # 直接抛出认证错误
            raise e
        except Exception as e:
            logger.error(f"认证过程中出现异常: {str(e)}")
            logger.error(traceback.format_exc())
            raise AuthenticationError(f"认证过程中出现异常: {str(e)}")

    async def send_request_raw(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送原始请求到 VTubeStudio 并等待响应

        Args:
            request_data: 请求数据字典

        Returns:
            Dict[str, Any]: 响应数据字典
        """
        if not self.websocket or not self._connected:
            raise ConnectionError("未连接到VTubeStudio")

        request_id = request_data.get("requestID", str(uuid.uuid4()))
        if "requestID" not in request_data:
            request_data["requestID"] = request_id

        request_json = json.dumps(request_data)
        logger.debug(f"发送请求: {request_json}")

        # 创建Future对象用于等待响应
        future = asyncio.Future()
        self.pending_requests[request_id] = future

        try:
            await self.websocket.send(request_json)
            # 等待响应，设置超时
            response = await asyncio.wait_for(future, timeout=30)
            return response
        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            raise ResponseError(
                f"请求超时: {request_data.get('messageType', 'Unknown')}"
            )
        except Exception as e:
            self.pending_requests.pop(request_id, None)
            raise ResponseError(f"发送请求失败: {str(e)}")

    async def send_request(self, request: VTSRequest) -> VTSResponse:
        """
        发送请求到 VTubeStudio

        Args:
            request: 请求对象

        Returns:
            响应对象
        """
        if not self.websocket or not self._connected:
            raise ConnectionError("未连接到VTubeStudio")

        request_id = str(uuid.uuid4())
        request_data = request.to_dict()
        request_data["requestID"] = request_id

        response_data = await self.send_request_raw(request_data)
        return VTSResponse.from_dict(response_data)

    async def _receive_messages(self) -> None:
        """接收并处理来自 VTubeStudio 的消息"""
        if not self.websocket:
            return

        try:
            while self._connected:
                try:
                    message = await self.websocket.recv()
                    logger.debug(f"收到消息: {message}")

                    try:
                        data = json.loads(message)

                        # 检查是否是响应消息
                        if (
                            "requestID" in data
                            and data["requestID"] in self.pending_requests
                        ):
                            request_id = data["requestID"]
                            future = self.pending_requests.pop(request_id)

                            # 检查future是否仍处于可设置结果的状态
                            if not future.done():
                                # 检查是否有错误
                                if "errorID" in data and data["errorID"]:
                                    error = APIError(data["errorID"])
                                    future.set_exception(error)
                                else:
                                    future.set_result(data)
                            else:
                                logger.debug(
                                    f"跳过对已完成future的结果设置，请求ID: {request_id}"
                                )

                        # 检查是否是事件消息
                        elif (
                            "messageType" in data
                            and data["messageType"] in self.event_callbacks
                        ):
                            event_type = data["messageType"]
                            callbacks = self.event_callbacks.get(event_type, [])
                            for callback in callbacks:
                                asyncio.create_task(callback(data))

                    except json.JSONDecodeError:
                        logger.error(f"无法解析JSON响应: {message}")
                    except Exception as e:
                        logger.error(f"处理消息时出错: {str(e)}")
                        logger.error(traceback.format_exc())

                except websockets.exceptions.ConnectionClosed:
                    logger.error("WebSocket连接已关闭")
                    self._connected = False
                    break
                except Exception as e:
                    logger.error(f"接收消息时出错: {str(e)}")
                    logger.error(traceback.format_exc())

        except asyncio.CancelledError:
            # 正常取消
            pass
        except Exception as e:
            logger.error(f"接收消息循环出错: {str(e)}")
            logger.error(traceback.format_exc())
        finally:
            # 确保所有挂起的请求都被取消
            for future in self.pending_requests.values():
                if not future.done():
                    future.set_exception(ConnectionError("连接已关闭"))
            self.pending_requests.clear()

    # --- 事件订阅方法 ---
    # --- 事件订阅方法 ---
    async def subscribe_to_event(
        self, event_name: str, config: Optional[Dict[str, Any]] = None
    ) -> EventSubscriptionResponse:
        """
        订阅 VTube Studio 事件。

        Args:
            event_name: 要订阅的事件名称 (例如 "ModelLoadedEvent")。
            config: 特定事件的配置字典 (如果需要)。

        Returns:
            EventSubscriptionResponse: 包含当前订阅列表的响应。

        Raises:
            ConnectionError: 如果未连接。
            APIError: 如果 VTS 返回订阅错误。
            ResponseError: 如果请求超时、失败或收到意外的响应类型。
        """
        logger.info(f"尝试订阅事件: {event_name}")
        if not self.is_authenticated:
            logger.warning("尝试在未认证的情况下订阅事件")
            raise AuthenticationError("需要先认证才能订阅事件")

        request = EventSubscriptionRequest(
            event_name=event_name, subscribe=True, config=config
        )
        response: VTSResponse = await self.send_request(request)

        # 首先检查是否有 API 错误
        if response.error:
            error_msg = response.data.get("message", f"错误代码: {response.error}")
            logger.error(f"订阅事件 {event_name} 失败 (API错误): {error_msg}")
            raise APIError(f"订阅事件失败: {error_msg}", error_id=response.error)

        # 检查消息类型是否符合预期
        if response.message_type == "EventSubscriptionResponse":
            # 手动构造 EventSubscriptionResponse
            specific_response = EventSubscriptionResponse(
                request_id=response.request_id,
                message_type=response.message_type,
                data=response.data,
                error=response.error,  # 这里应该是 None
                subscribed_event_count=response.data.get("subscribedEventCount", 0),
                subscribed_events=response.data.get("subscribedEvents", []),
            )
            # 更新本地订阅列表
            self.subscribed_events = specific_response.subscribed_events
            logger.info(
                f"成功订阅事件: {event_name}。当前订阅数: {specific_response.subscribed_event_count}"
            )
            return specific_response
        else:
            # 收到非预期的成功响应类型
            logger.error(
                f"订阅事件 {event_name} 收到非预期响应类型: {response.message_type}"
            )
            raise ResponseError(f"订阅事件收到非预期响应类型: {response.message_type}")

    async def unsubscribe_from_event(
        self, event_name: Optional[str] = None
    ) -> EventSubscriptionResponse:
        """
        取消订阅 VTube Studio 事件。

        Args:
            event_name: 要取消订阅的事件名称。如果为 None，则取消订阅所有事件。

        Returns:
            EventSubscriptionResponse: 包含当前订阅列表的响应。

        Raises:
            ConnectionError: 如果未连接。
            APIError: 如果 VTS 返回取消订阅错误。
            ResponseError: 如果请求超时、失败或收到意外的响应类型。
        """
        log_msg = f"尝试取消订阅事件: {event_name if event_name else '所有事件'}"
        logger.info(log_msg)
        if not self.is_authenticated:
            logger.warning("尝试在未认证的情况下取消订阅事件")
            raise AuthenticationError("需要先认证才能取消订阅事件")

        request = EventSubscriptionRequest(event_name=event_name, subscribe=False)
        response: VTSResponse = await self.send_request(request)

        # 首先检查是否有 API 错误
        if response.error:
            error_msg = response.data.get("message", f"错误代码: {response.error}")
            logger.error(
                f"取消订阅事件 {event_name if event_name else '所有'} 失败 (API错误): {error_msg}"
            )
            raise APIError(f"取消订阅事件失败: {error_msg}", error_id=response.error)

        # 检查消息类型是否符合预期
        if response.message_type == "EventSubscriptionResponse":
            # 手动构造 EventSubscriptionResponse
            specific_response = EventSubscriptionResponse(
                request_id=response.request_id,
                message_type=response.message_type,
                data=response.data,
                error=response.error,  # 这里应该是 None
                subscribed_event_count=response.data.get("subscribedEventCount", 0),
                subscribed_events=response.data.get("subscribedEvents", []),
            )
            # 更新本地订阅列表
            self.subscribed_events = specific_response.subscribed_events
            logger.info(
                f"成功取消订阅事件: {event_name if event_name else '所有事件'}。当前订阅数: {specific_response.subscribed_event_count}"
            )
            return specific_response
        else:
            # 收到非预期的成功响应类型
            logger.error(
                f"取消订阅事件 {event_name if event_name else '所有'} 收到非预期响应类型: {response.message_type}"
            )
            raise ResponseError(
                f"取消订阅事件收到非预期响应类型: {response.message_type}"
            )

    # --- 事件回调注册 ---
    def register_event_callback(
        self,
        event_type: str,
        callback: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]],
    ) -> None:
        """
        注册事件回调函数。注意：这只在本地注册回调，需要调用 subscribe_to_event 来实际接收事件。

        Args:
            event_type: 事件类型 (例如 "ModelLoadedEvent")。
            callback: 回调函数 (async def callback(event_data: dict))。
        """
        if not event_type.endswith("Event"):
            logger.warning(
                f"注册的回调事件类型 '{event_type}' 可能不是有效的事件名称 (不以 'Event' 结尾)"
            )
        if event_type not in self.event_callbacks:
            self.event_callbacks[event_type] = []
        if callback not in self.event_callbacks[event_type]:
            self.event_callbacks[event_type].append(callback)
            logger.info(f"已注册事件 '{event_type}' 的回调函数: {callback.__name__}")
        else:
            logger.warning(
                f"尝试重复注册事件 '{event_type}' 的回调函数: {callback.__name__}"
            )

    def unregister_event_callback(
        self,
        event_type: str,
        callback: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]],
    ) -> None:
        """
        取消注册事件回调函数。

        Args:
            event_type: 事件类型。
            callback: 要取消注册的回调函数。
        """
        if (
            event_type in self.event_callbacks
            and callback in self.event_callbacks[event_type]
        ):
            self.event_callbacks[event_type].remove(callback)
            logger.info(
                f"已取消注册事件 '{event_type}' 的回调函数: {callback.__name__}"
            )
            if not self.event_callbacks[event_type]:
                # 如果该事件类型没有回调了，可以考虑从字典中移除
                del self.event_callbacks[event_type]
        else:
            logger.warning(
                f"尝试取消注册不存在的回调函数或事件类型: {event_type} / {callback.__name__}"
            )
