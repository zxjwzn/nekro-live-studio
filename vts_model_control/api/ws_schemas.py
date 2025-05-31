from typing import List, Optional, Union
from pydantic import BaseModel, Field
from configs.config import config


class SayData(BaseModel):
    """说话行为的数据模型"""

    text: List[str] = Field(description="要说的文本列表")
    speed: List[float] = Field(description="每段文本的速度列表")
    delay: float = Field(default=0.0, description="延迟执行的时间(秒)")


class AnimationParameter(BaseModel):
    """单个动画参数的数据模型"""

    parameter: str = Field(description="VTS模型参数名称")
    from_value: Optional[float] = Field(
        default=None, alias="from", description="参数起始值"
    )
    to: Optional[float] = Field(default=None, description="参数目标值")
    duration: float = Field(description="动画持续时间(秒)")
    delay: float = Field(default=0.0, description="延迟执行的时间(秒)")
    easing: str = Field(default="linear", description="缓动函数名称")


class EmotionData(BaseModel):
    """表情动作的数据模型"""

    name: Optional[str] = Field(
        default=None, description="表情文件名，如果为空则返回所有表情列表"
    )
    duration: float = Field(default=0.0, description="表情持续时间(秒)")
    delay: float = Field(default=0.0, description="延迟执行的时间(秒)")


class ExecuteData(BaseModel):
    """执行命令的数据模型"""

    loop: int = Field(default=0, description="循环次数，0表示不循环")


class SayAction(BaseModel):
    """说话行为消息"""

    type: str = "say"
    data: SayData


class AnimationAction(BaseModel):
    """动画行为消息"""

    type: str = "animation"
    data: Union[AnimationParameter, List[AnimationParameter]]


class EmotionAction(BaseModel):
    """表情行为消息"""

    type: str = "emotion"
    data: EmotionData


class ExecuteAction(BaseModel):
    """执行命令消息"""

    type: str = "execute"
    data: ExecuteData = Field(default_factory=ExecuteData)


class ClearAction(BaseModel):
    """清空命令消息"""

    type: str = "clear"


class Danmaku(BaseModel):
    from_live_room: int = Field(
        default=config.bilibili_configs.live_room_id, description="消息来源(房间号)"
    )
    uid: str = Field(default="0", description="消息用户ID")
    username: str = Field(default="unknown", description="用户名")
    text: str = Field(default="", description="弹幕内容")
    time: int = Field(default=0, description="弹幕发送时间")
    url: List[str] = Field(default_factory=list, description="弹幕中的表情图片url列表")
    is_trigget: bool = Field(
        default=True, description="是否触发LLM (由ws客户端接收并处理)"
    )
    is_system: bool = Field(
        default=False, description="是否作为system身份发送 (由ws客户端接收并处理)"
    )


# 用于区分消息类型的联合类型
WSMessage = Union[SayAction, AnimationAction, EmotionAction, ExecuteAction, ClearAction]
