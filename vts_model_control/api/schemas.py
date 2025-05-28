from pydantic import BaseModel, Field
from typing import List, Optional, Union, Literal, Annotated
from configs.config import config


class BaseAction(BaseModel):
    startTime: float = Field(default=0.0, description="动作开始时间，单位秒")


class SayAction(BaseAction):
    type: Literal["say"] = "say"
    text: List[str] = Field(description="要朗读的文本内容列表")
    speeds: Optional[List[float]] = Field(
        default=None, description="对应每段文本的播放速率（字/秒）列表，可选"
    )


class AnimateAction(BaseAction):
    type: Literal["animation"] = "animation"
    parameter: str = Field(description="VTube Studio中的参数名")
    from_value: Optional[float] = Field(None, alias="from", description="参数起始值")
    to: float = Field(description="参数目标值")
    duration: float = Field(default=1.0, description="动画持续时间，单位秒")
    easing: str = Field(default="linear", description="缓动函数类型")


class EmotionAction(BaseAction):
    type: Literal["emotion"] = "emotion"
    name: str = Field(description="要激活的表情名称")
    duration: float = Field(
        default=0.0, description="表情持续时间，单位秒；<=0 表示永久设置"
    )
    startTime: float = Field(default=0.0, description="表情的起始时间")


class AnimationRequest(BaseModel):
    actions: List[
        Annotated[
            Union[SayAction, AnimateAction, EmotionAction], Field(discriminator="type")
        ]
    ]
    loop: int = Field(
        default=0,
        description="循环次数，0表示不循环，-1表示无限循环，正数表示具体循环次数",
    )


class Danmaku(BaseModel):
    from_live_room: int = Field(
        default=config.bilibili_configs.live_room_id, description="消息来源(房间号)"
    )
    uid: str = Field(default="0", description="消息用户ID")
    username: str = Field(default="unknown", description="用户名")
    text: str = Field(default="", description="弹幕内容")
    time: int = Field(default=0, description="弹幕发送时间")
    url: str = Field(default="", description="弹幕中的图片url 没有则留空")
    is_trigget: bool = Field(
        default=True, description="是否触发LLM (由ws客户端接收并处理)"
    )
    is_system: bool = Field(
        default=False, description="是否作为system身份发送 (由ws客户端接收并处理)"
    )
