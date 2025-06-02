"""
VTubeStudio 客户端模块 - 修复版
"""

from .client import VTSClient
from .exceptions import (
    VTSAPIError,
    VTSAuthenticationError,
    VTSConnectionError,
    VTSException,
    VTSRequestError,
    VTSResponseError,
)  # noqa: F401
from .models import (
    APIStateRequest,  # noqa: F401
    AuthenticationRequest,  # noqa: F401
    AuthenticationTokenRequest,  # noqa: F401
    AvailableLive2dParametersRequest,  # noqa: F401
    AvailableModelsRequest,  # noqa: F401
    AvailableParametersRequest,  # noqa: F401
    CurrentModelRequest,  # noqa: F401
    ExpressionActivationRequest,  # noqa: F401
    ExpressionListRequest,  # noqa: F401
    FaceFoundRequest,  # noqa: F401
    HotkeysRequest,  # noqa: F401
    ModelLoadRequest,  # noqa: F401
    MoveModelRequest,  # noqa: F401
    ParameterValueRequest,  # noqa: F401
    SetParameterValueRequest,  # noqa: F401
    StatisticsRequest,  # noqa: F401
    TriggerHotkeyRequest,  # noqa: F401
    VTSFolderInfoRequest,  # noqa: F401
    VTSRequest,
    VTSResponse,  # noqa: F401
)
from .plugin import VTSPlugin

__all__ = [
    "VTSAPIError",
    "VTSAuthenticationError",
    "VTSClient",
    "VTSConnectionError",
    "VTSException",
    "VTSPlugin",
    "VTSRequest",
    "VTSRequestError",
    "VTSResponse",
    "VTSResponseError",
]
