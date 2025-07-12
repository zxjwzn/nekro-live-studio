"""
VTubeStudio 插件高级接口
"""

import contextlib
from typing import Any, Callable, Coroutine, Dict, List, Optional  # noqa: F401

from ...configs.config import config
from ...utils.logger import logger
from .client import VTSClient
from .models import (
    APIStateRequest,
    AvailableLive2dParametersRequest,
    AvailableModelsRequest,
    AvailableParametersRequest,
    CurrentModelRequest,
    EventSubscriptionResponse,
    ExpressionActivationRequest,
    ExpressionListRequest,
    FaceFoundRequest,
    HotkeysRequest,
    ModelLoadRequest,
    MoveModelRequest,
    ParameterCreationRequest,
    ParameterValueRequest,
    SetParameterValueRequest,
    StatisticsRequest,
    TriggerHotkeyRequest,
    VTSFolderInfoRequest,
)


class VTSPlugin:
    """VTubeStudio 插件高级接口

    提供更高级别的方法来与 VTube Studio API 交互。
    """

    def __init__(
        self,
        plugin_name: str,
        plugin_developer: str,
        plugin_icon: Optional[str] = None,
        endpoint: str = "ws://localhost:8001",
    ):
        """
        初始化 VTubeStudio 插件

        Args:
            plugin_name: 插件名称 (3-32 个字符)
            plugin_developer: 插件开发者 (3-32 个字符)
            plugin_icon: 插件图标 (可选, base64 编码的 128x128 PNG/JPG)
            endpoint: VTubeStudio WebSocket 端点
        """
        self.client = VTSClient(
            plugin_name=plugin_name,
            plugin_developer=plugin_developer,
            plugin_icon=plugin_icon,
            endpoint=endpoint,
        )

    async def connect_and_authenticate(self, authentication_token: Optional[str] = None) -> bool:
        """
        连接到 VTube Studio 并执行认证流程。

        Returns:
            bool: 连接和认证是否成功。

        Raises:
            ConnectionError: 连接失败。
            AuthenticationError: 认证失败。
            APIError: VTS 返回 API 错误。
            ResponseError: 请求超时或响应错误。
        """
        try:
            await self.client.connect()
            return await self.client.authenticate(authentication_token)
        except Exception:
            logger.exception("连接并认证失败")
            # 确保断开连接
            with contextlib.suppress(Exception):
                await self.client.disconnect()
            return False

    async def disconnect(self) -> None:
        """断开与 VTube Studio 的连接。"""
        await self.client.disconnect()

    # --- General API Methods ---

    async def get_statistics(self) -> Dict[str, Any]:
        """获取当前 VTS 统计信息 (如版本、FPS、插件数等)。"""
        response = await self.client.send_request(StatisticsRequest())
        return response.data

    async def get_folder_info(self) -> Dict[str, Any]:
        """获取 VTube Studio 各主要文件夹的名称 (相对于 StreamingAssets)。"""
        response = await self.client.send_request(VTSFolderInfoRequest())
        return response.data

    async def get_api_state(self) -> Dict[str, Any]:
        """获取当前 VTube Studio API 状态。"""
        response = await self.client.send_request(APIStateRequest())
        return response.data

    # --- Model Related Methods ---

    async def get_current_model(self) -> Dict[str, Any]:
        """获取当前加载的模型信息。
        如果未加载模型，'modelLoaded' 将为 false。
        """
        response = await self.client.send_request(CurrentModelRequest())
        return response.data

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """获取所有可用 VTS 模型的列表。"""
        response = await self.client.send_request(AvailableModelsRequest())
        return response.data.get("availableModels", [])

    async def load_model(self, model_id: str) -> Dict[str, Any]:
        """通过模型 ID 加载 VTS 模型。
        如果传入空 model_id，将卸载当前模型。
        """
        response = await self.client.send_request(ModelLoadRequest(model_id))
        return response.data

    async def move_model(
        self,
        time_in_seconds: float,
        values_are_relative_to_model: bool,
        position_x: Optional[float] = None,
        position_y: Optional[float] = None,
        rotation: Optional[float] = None,
        size: Optional[float] = None,
    ) -> Dict[str, Any]:
        """移动当前加载的 VTS 模型。
        未提供的参数将保持不变。
        参考文档中的坐标系说明。

        Args:
            time_in_seconds: 移动动画的持续时间 (0 到 2 秒)。0 表示瞬时移动。
            values_are_relative_to_model: 如果为 True，则提供的 X/Y/Rotation/Size 值是相对于当前值的增量；否则为绝对值。
            position_x: 目标 X 坐标 (-1000 到 1000)。
            position_y: 目标 Y 坐标 (-1000 到 1000)。
            rotation: 目标旋转角度 (-360 到 360)。
            size: 目标尺寸 (-100 到 100)。
        """
        
        request = MoveModelRequest(
            time_in_seconds=time_in_seconds,
            values_are_relative_to_model=values_are_relative_to_model,
            positionX=position_x,
            positionY=position_y,
            rotation=rotation,
            size=size,
        )
        response = await self.client.send_request(request)
        return response.data  # 成功时为空

    # --- Parameter Related Methods ---

    async def get_available_parameters(self) -> List[Dict[str, Any]]:
        """获取所有可用的输入参数列表 (包括默认参数和自定义参数)。"""
        response = await self.client.send_request(AvailableParametersRequest())
        # 返回包含默认和自定义参数的完整列表
        return response.data.get("defaultParameters", []) + response.data.get("customParameters", [])

    async def get_live2d_parameters(self) -> List[Dict[str, Any]]:
        """获取当前加载模型的所有 Live2D 参数及其当前值。"""
        response = await self.client.send_request(AvailableLive2dParametersRequest())
        return response.data.get("parameters", [])

    async def get_parameter_value(self, parameter_name: str) -> Dict[str, Any]:
        """获取指定输入参数（默认或自定义）的详细信息 (包括值、范围、默认值等)。"""
        response = await self.client.send_request(ParameterValueRequest(parameter_name))
        return response.data

    async def set_parameter_value(
        self,
        parameter_name: str,
        value: float,
        weight: float = 1.0,
        mode: str = "set",
        face_found: bool = True,
    ) -> Dict[str, Any]:
        """为默认或自定义参数注入数据。

        Args:
            parameter_name: 参数 ID。
            value: 要设置的值。
            weight: (仅当 mode='set') 混合权重 (0-1)。1 表示完全覆盖。
            mode: 'set' (设置/覆盖) 或 'add' (添加到当前值)。
        """
        request = SetParameterValueRequest(parameter_name, value, weight=weight, mode=mode, face_found=face_found)
        response = await self.client.send_request(request)
        return response.data  # 成功时为空

    async def create_parameter(
        self,
        parameter_name: str,
        min_value: float,
        max_value: float,
        default_value: float,
        explanation: Optional[str] = None,
    ) -> Dict[str, Any]:
        """创建新的自定义输入参数。

        Args:
            parameter_name: 参数名称 (字母数字，4-32字符，无空格)。
            min_value: 参数映射时的默认最小值 (-1000000 到 1000000)。
            max_value: 参数映射时的默认最大值 (-1000000 到 1000000)。
            default_value: 参数映射时的默认值 (-1000000 到 1000000)。
            explanation: (可选) 参数的简短说明 (<256 字符)。
        """
        request = ParameterCreationRequest(parameter_name, min_value, max_value, default_value, explanation)
        response = await self.client.send_request(request)
        return response.data

    # --- Expression Related Methods ---

    async def get_expressions(self, expression_file: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取当前模型中所有表情或指定表情的状态列表。"""
        response = await self.client.send_request(ExpressionListRequest(expression_file))
        return response.data.get("expressions", [])

    async def activate_expression(self, expression_file: str, active: bool = True, fade_time: float = 0.25) -> Dict[str, Any]:
        """激活或停用指定表情文件。

        Args:
            expression_file: 表情文件名 (例如 "myExpression.exp3.json")。
            active: True 激活, False 停用。
            fade_time: 激活时的淡入时间 (0-2 秒)。停用时使用相同的淡出时间。
        """
        request = ExpressionActivationRequest(expression_file, active, fade_time)
        response = await self.client.send_request(request)
        return response.data  # 成功时为空

    # --- Hotkey Related Methods ---

    async def get_hotkeys(
        self,
        model_id: Optional[str] = None,
        live_2d_item_file_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取当前模型、指定模型或指定 Live2D 物品的可用热键列表。"""
        # 使用修正后的 HotkeysRequest 参数名
        request = HotkeysRequest(model_id=model_id, live2DItemFileName=live_2d_item_file_name)
        response = await self.client.send_request(request)
        return response.data.get("availableHotkeys", [])

    async def trigger_hotkey(self, hotkey_id: str, item_instance_id: Optional[str] = None) -> Dict[str, Any]:
        """触发指定的热键。

        Args:
            hotkey_id: 热键的名称或唯一 ID。
            item_instance_id: (可选) 如果要在 Live2D 物品上触发热键，请提供其物品实例 ID。
        """
        # 使用修正后的 TriggerHotkeyRequest 参数名
        request = TriggerHotkeyRequest(hotkey_id=hotkey_id, itemInstanceID=item_instance_id)
        response = await self.client.send_request(request)
        return response.data

    # --- Tracking Related Methods ---

    async def is_face_found(self) -> bool:
        """检查面部追踪器当前是否检测到人脸。"""
        response = await self.client.send_request(FaceFoundRequest())
        return response.data.get("found", False)

    # --- Event Handling Methods ---

    def register_event_handler(
        self,
        event_type: str,
        handler: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]],
    ) -> None:
        """
        注册事件回调函数 (本地注册)。
        注意：还需要调用 subscribe_event 来实际从 VTube Studio 接收该事件。

        Args:
            event_type: 事件类型 (例如 "ModelLoadedEvent")。
            handler: 异步回调函数 (async def handler(event_data: dict))。
        """
        self.client.register_event_callback(event_type, handler)

    def unregister_event_handler(
        self,
        event_type: str,
        handler: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]],
    ) -> None:
        """
        取消注册事件回调函数 (本地取消注册)。
        如果不再需要接收该事件，还应调用 unsubscribe_event。

        Args:
            event_type: 事件类型。
            handler: 要取消注册的回调函数。
        """
        self.client.unregister_event_callback(event_type, handler)

    async def subscribe_event(self, event_name: str, config: Optional[Dict[str, Any]] = None) -> EventSubscriptionResponse:
        """
        向 VTube Studio 订阅指定事件。

        Args:
            event_name: 要订阅的事件名称。
            config: 特定事件的配置 (如果需要)。

        Returns:
            EventSubscriptionResponse: 订阅响应。
        """
        return await self.client.subscribe_to_event(event_name, config)

    async def unsubscribe_event(self, event_name: Optional[str] = None) -> EventSubscriptionResponse:
        """
        向 VTube Studio 取消订阅指定事件或所有事件。

        Args:
            event_name: 要取消订阅的事件名称。如果为 None，则取消订阅所有事件。

        Returns:
            EventSubscriptionResponse: 取消订阅响应。
        """
        return await self.client.unsubscribe_from_event(event_name)

plugin: VTSPlugin = VTSPlugin(
    plugin_name=config.PLUGIN.PLUGIN_NAME,
    plugin_developer=config.PLUGIN.PLUGIN_DEVELOPER,
    endpoint=config.PLUGIN.VTS_ENDPOINT,
)