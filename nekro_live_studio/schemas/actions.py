from typing import Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, Field

from ..configs.config import config


class SoundPlayData(BaseModel):
    """音频播放数据配置"""

    path: str = Field(default="", description="音效路径, 如果为空则返回所有音效列表")
    duration: float = Field(default=0.0, description="持续时间,为0则完整播放直至结束", ge=0)
    volume: float = Field(default=1.0, description="音量,范围为0~1", ge=0, le=1)
    speed: float = Field(default=1.0, description="播放速度,默认为1", gt=0)
    delay: float = Field(default=0.0, description="延迟执行的时间(秒)", ge=0)


class SayData(BaseModel):
    text: str = Field(description="要说的文本")
    speed: float = Field(description="文本的播放速度, 代表1秒n字", default=config.SUBTITLE.TEXT_PER_SECOND_RATE)
    font_size: int = Field(description="字体大小", default=config.SUBTITLE.FONT_SIZE)
    tts_text: str = Field(description="文本转语音的文字内容")
    font_color: str = Field(description="字体颜色, 16进制颜色码", default=config.SUBTITLE.FONT_COLOR)
    font_path: str = Field(description="字体路径", default=config.SUBTITLE.FONT_PATH)
    font_edge_color: str = Field(description="字体描边颜色, 16进制颜色码", default=config.SUBTITLE.FONT_EDGE_COLOR)
    font_edge_width: int = Field(description="字体描边宽度", default=config.SUBTITLE.FONT_EDGE_WIDTH)
    volume: float = Field(default=config.TTS.VOLUME, description="音量,范围为0~1", ge=0, le=1)


class AnimationData(BaseModel):
    parameter: str = Field(description="VTS模型参数名称")
    from_value: Optional[float] = Field(
        default=None,
        description="参数起始值",
    )
    target: float = Field(default=0, description="参数目标值")
    duration: float = Field(description="动画持续时间(秒)")
    delay: float = Field(default=0.0, description="延迟执行的时间(秒)")
    easing: str = Field(default="linear", description="缓动函数名称")
    priority: int = Field(default=0, description="缓动优先级, 0是最低")


class ExpressionData(BaseModel):
    name: str = Field(
        default="",
        description="表情文件名，如果为空则返回所有表情列表",
    )
    duration: float = Field(default=0.0, description="表情持续时间(秒), 小于等于0则未永久设置")
    delay: float = Field(default=0.0, description="延迟执行的时间(秒)")


class ExecuteData(BaseModel):
    loop: int = Field(default=0, description="循环次数，0表示执行一次, 1表示执行两次, 以此类推")


class PlayPreformAnimationData(BaseModel):
    """播放动画模板的数据"""

    name: str = Field(description="要播放的动画模板名称")
    params: Optional[Dict[str, Any]] = Field(default=None, description="传递给动画模板的外部参数")
    delay: float = Field(default=0.0, description="整个动画模板的起始延迟(秒)")


class ListPreformAnimationData(BaseModel):
    """列出动画模板的数据"""


class GetSounds(BaseModel):
    type: Literal["get_sounds"]


class GetExpressions(BaseModel):
    type: Literal["get_expressions"]


class SoundPlay(BaseModel):
    type: Literal["sound_play"]
    data: SoundPlayData


class Say(BaseModel):
    """说话行为"""

    type: Literal["say"]
    data: SayData


class Animation(BaseModel):
    """动画行为"""

    type: Literal["animation"]
    data: AnimationData


class Expression(BaseModel):
    """表情行为"""

    type: Literal["expression"]
    data: ExpressionData


class Execute(BaseModel):
    """执行命令行为"""

    type: Literal["execute"]
    data: ExecuteData = Field(default_factory=ExecuteData)


class PlayPreformAnimation(BaseModel):
    """播放动画模板的行为"""

    type: Literal["play_preformed_animation"]
    data: PlayPreformAnimationData


class ListPreformAnimation(BaseModel):
    """列出所有可用动画模板的行为"""

    type: Literal["list_preformed_animations"]
    data: ListPreformAnimationData = Field(default_factory=ListPreformAnimationData)

class ResponseMessage(BaseModel):
    """响应消息"""

    status: Literal["success", "error"]
    message: str
    data: Optional[Any] = None

Action = Union[
    Say, Animation, Expression, Execute, SoundPlay, PlayPreformAnimation,
]
