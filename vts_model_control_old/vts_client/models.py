"""
VTubeStudio 数据模型
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class VTSRequest:
    """VTubeStudio API请求基类"""

    message_type: str
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        request_dict: Dict[str, Any] = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "messageType": self.message_type,
        }
        if self.data:
            request_dict["data"] = self.data
        return request_dict


@dataclass
class VTSResponse:
    """VTubeStudio API响应基类"""

    request_id: str
    message_type: str
    data: Dict[str, Any]
    error: Optional[int] = None  # Error ID 是整数

    @classmethod
    def from_dict(cls, response_dict: Dict[str, Any]) -> "VTSResponse":
        # 从 data 字段中获取 errorID
        error_id = response_dict.get("data", {}).get("errorID")
        return cls(
            request_id=response_dict.get("requestID", ""),
            message_type=response_dict.get("messageType", ""),
            data=response_dict.get("data", {}),
            error=error_id,  # 使用提取的 error_id
        )


@dataclass
class StatisticsRequest(VTSRequest):
    """获取当前 VTS 统计信息请求"""

    def __init__(self):
        super().__init__(message_type="StatisticsRequest")


@dataclass
class VTSFolderInfoRequest(VTSRequest):
    """获取 VTube Studio 各文件夹名称请求"""

    def __init__(self):
        super().__init__(message_type="VTSFolderInfoRequest")


@dataclass
class APIStateRequest(VTSRequest):
    """检查 API 状态请求"""

    def __init__(self):
        super().__init__(message_type="APIStateRequest")


@dataclass
class AuthenticationTokenRequest(VTSRequest):
    """请求认证令牌"""

    def __init__(
        self, plugin_name: str, plugin_developer: str, plugin_icon: Optional[str] = None
    ):
        data = {"pluginName": plugin_name, "pluginDeveloper": plugin_developer}
        if plugin_icon:
            data["pluginIcon"] = plugin_icon
        super().__init__(message_type="AuthenticationTokenRequest", data=data)


@dataclass
class AuthenticationRequest(VTSRequest):
    """使用认证令牌进行认证"""

    def __init__(
        self,
        plugin_name: str,
        plugin_developer: str,
        authentication_token: str,
        plugin_icon: Optional[str] = None,
    ):
        data = {
            "pluginName": plugin_name,
            "pluginDeveloper": plugin_developer,
            "authenticationToken": authentication_token,
        }
        if plugin_icon:
            data["pluginIcon"] = plugin_icon
        super().__init__(message_type="AuthenticationRequest", data=data)


@dataclass
class CurrentModelRequest(VTSRequest):
    """获取当前加载的模型信息请求"""

    def __init__(self):
        super().__init__(message_type="CurrentModelRequest")


@dataclass
class AvailableParametersRequest(VTSRequest):
    """请求可用输入参数列表（包括默认参数和自定义参数）"""

    def __init__(self):
        super().__init__(message_type="InputParameterListRequest")


@dataclass
class AvailableLive2dParametersRequest(VTSRequest):
    """获取当前模型的所有 Live2D 参数值请求"""

    def __init__(self):
        super().__init__(message_type="Live2DParameterListRequest")


@dataclass
class ParameterValueRequest(VTSRequest):
    """获取指定参数（默认或自定义）的值请求"""

    def __init__(self, parameter_name: str):
        super().__init__(
            message_type="ParameterValueRequest", data={"name": parameter_name}
        )


@dataclass
class SetParameterValueRequest(VTSRequest):
    """为默认或自定义参数注入数据请求
    mode: 'set' (覆盖) 或 'add' (增加)
    weight: 仅在 mode='set' 时有效, 0到1之间，用于混合API值和原始跟踪值
    """

    def __init__(
        self,
        parameter_name: str,
        value: float,
        weight: float = 1.0,
        mode: str = "set",
        face_found: bool = True,
    ):
        super().__init__(
            message_type="InjectParameterDataRequest",
            data={
                "faceFound": face_found,
                "mode": mode,
                "parameterValues": [
                    {"id": parameter_name, "value": value, "weight": weight}
                ],
            },
        )


@dataclass
class ParameterCreationRequest(VTSRequest):
    """创建新的自定义参数请求
    parameter_name: 参数名称 (字母数字，4-32字符)
    explanation: 参数说明 (可选，<256字符)
    min_value, max_value: 参数映射时的默认范围 (-1000000 到 1000000)
    default_value: 参数映射时的默认值 (-1000000 到 1000000)
    """

    def __init__(
        self,
        parameter_name: str,
        min_value: float,
        max_value: float,
        default_value: float,
        explanation: Optional[str] = None,
    ):
        data = {
            "parameterName": parameter_name,
            "min": min_value,
            "max": max_value,
            "defaultValue": default_value,
        }
        if explanation:
            data["explanation"] = explanation
        super().__init__(message_type="ParameterCreationRequest", data=data)


@dataclass
class ExpressionListRequest(VTSRequest):
    """请求表情状态列表
    expression_file: 可选，指定表情文件名以获取单个表情状态，否则返回所有表情状态
    """

    def __init__(self, expression_file: Optional[str] = None):
        data: Dict[str, Any] = {"details": True}
        if expression_file:
            data["expressionFile"] = expression_file
        super().__init__(message_type="ExpressionStateRequest", data=data)


@dataclass
class ExpressionActivationRequest(VTSRequest):
    """请求激活或停用表情
    fade_time: 激活时的淡入时间（秒），范围0-2。停用时使用与激活时相同的淡入时间。
    """

    def __init__(
        self, expression_file: str, active: bool = True, fade_time: float = 0.25
    ):
        super().__init__(
            message_type="ExpressionActivationRequest",
            data={
                "expressionFile": expression_file,
                "active": active,
                "fadeTime": fade_time,
            },
        )


@dataclass
class HotkeysRequest(VTSRequest):
    """请求当前模型或指定模型的可用热键列表
    model_id: 可选，指定模型ID，否则返回当前加载模型的列表
    live2DItemFileName: 可选，指定 Live2D 物品文件名以获取其热键列表
    """

    def __init__(
        self, model_id: Optional[str] = None, live2DItemFileName: Optional[str] = None
    ):
        data = {}
        if model_id:
            data["modelID"] = model_id
        elif live2DItemFileName:
            data["live2DItemFileName"] = live2DItemFileName
        # 如果 data 为空，则不传递 data 字段
        super().__init__(
            message_type="HotkeysInCurrentModelRequest", data=data if data else None
        )


@dataclass
class TriggerHotkeyRequest(VTSRequest):
    """请求执行热键
    hotkey_id: 要执行的热键的名称或唯一ID
    itemInstanceID: 可选，指定 Live2D 物品的实例ID，以在该物品上触发热键
    """

    def __init__(self, hotkey_id: str, itemInstanceID: Optional[str] = None):
        data = {"hotkeyID": hotkey_id}
        if itemInstanceID:
            data["itemInstanceID"] = itemInstanceID
        super().__init__(message_type="HotkeyTriggerRequest", data=data)


@dataclass
class AvailableModelsRequest(VTSRequest):
    """获取可用 VTS 模型列表请求"""

    def __init__(self):
        super().__init__(message_type="AvailableModelsRequest")


@dataclass
class ModelLoadRequest(VTSRequest):
    """通过模型 ID 加载 VTS 模型请求"""

    def __init__(self, model_id: str):
        super().__init__(message_type="ModelLoadRequest", data={"modelID": model_id})


@dataclass
class MoveModelRequest(VTSRequest):
    """移动当前加载的 VTS 模型请求
    time_in_seconds: 移动所需时间（秒），0-2
    values_are_relative_to_model: 值是否相对于模型当前位置
    positionX, positionY: 目标 X, Y 坐标 (-1000 到 1000)
    rotation: 目标旋转角度 (-360 到 360)
    size: 目标大小 (-100 到 100)
    """

    def __init__(
        self,
        time_in_seconds: float,
        values_are_relative_to_model: bool,
        positionX: Optional[float] = None,
        positionY: Optional[float] = None,
        rotation: Optional[float] = None,
        size: Optional[float] = None,
    ):
        data = {
            "timeInSeconds": time_in_seconds,
            "valuesAreRelativeToModel": values_are_relative_to_model,
        }
        # 只有当提供了值时才添加到 data 字典中
        if positionX is not None:
            data["positionX"] = positionX
        if positionY is not None:
            data["positionY"] = positionY
        if rotation is not None:
            data["rotation"] = rotation
        if size is not None:
            data["size"] = size
        super().__init__(message_type="MoveModelRequest", data=data)


@dataclass
class FaceFoundRequest(VTSRequest):
    """检查人脸是否当前被追踪器找到请求"""

    def __init__(self):
        super().__init__(message_type="FaceFoundRequest")


@dataclass
class EventSubscriptionRequest(VTSRequest):
    """事件订阅/取消订阅请求
    event_name: 要订阅/取消订阅的事件名称。如果 subscribe=False 且 event_name 为 None 或空，则取消订阅所有事件。
    subscribe: True 表示订阅，False 表示取消订阅。
    config: 特定事件的配置字典，默认为空。
    """

    def __init__(
        self,
        event_name: Optional[str],
        subscribe: bool,
        config: Optional[Dict[str, Any]] = None,
    ):
        data: Dict[str, Any] = {"subscribe": subscribe}
        if event_name:
            data["eventName"] = event_name
        if config is not None:
            data["config"] = config
        else:
            # 确保即使没有配置，也发送一个空的 config 对象
            data["config"] = {}

        super().__init__(message_type="EventSubscriptionRequest", data=data)


@dataclass
class EventSubscriptionResponse(VTSResponse):
    """事件订阅/取消订阅响应"""

    subscribed_event_count: int = 0
    subscribed_events: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, response_dict: Dict[str, Any]) -> "EventSubscriptionResponse":
        base_response = super().from_dict(response_dict)
        return cls(
            request_id=base_response.request_id,
            message_type=base_response.message_type,
            data=base_response.data,
            error=base_response.error,
            subscribed_event_count=base_response.data.get("subscribedEventCount", 0),
            subscribed_events=base_response.data.get("subscribedEvents", []),
        )
