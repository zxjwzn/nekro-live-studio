"""
VTubeStudio 客户端异常类
"""


class VTSException(Exception):
    """VTubeStudio 客户端基础异常类"""

    pass


class ConnectionError(VTSException):
    """连接错误"""

    pass


class AuthenticationError(VTSException):
    """认证错误"""

    pass


class RequestError(VTSException):
    """请求错误"""

    pass


class ResponseError(VTSException):
    """响应错误"""

    pass


class APIError(VTSException):
    """API错误"""

    def __init__(self, error_message, error_id=None):
        self.error_message = error_message
        self.error_id = error_id
        super().__init__(f"API错误: {error_message}")
