"""
VTubeStudio 客户端异常类
"""


class VTSException(Exception):
    """VTubeStudio 客户端基础异常类"""



class VTSConnectionError(VTSException):
    """连接错误"""



class VTSAuthenticationError(VTSException):
    """认证错误"""



class VTSRequestError(VTSException):
    """请求错误"""



class VTSResponseError(VTSException):
    """响应错误"""



class VTSAPIError(VTSException):
    """API错误"""

    def __init__(self, error_message, error_id=None):
        self.error_message = error_message
        self.error_id = error_id
        super().__init__(f"API错误: {error_message}")
