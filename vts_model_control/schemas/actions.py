from typing import List, Literal, Optional, Union

from configs.config import config
from pydantic import BaseModel, Field


class SoundPlayData(BaseModel):
    """音频播放数据配置"""
    path: Optional[str] = Field(default=None, description="音效路径, 如果为空则返回所有音效列表")
    duration: float = Field(default=0.0, description="持续时间,为0则完整播放直至结束", ge=0)
    volume: float = Field(default=1.0, description="音量,范围为0~1", ge=0, le=1)
    speed: float = Field(default=1.0, description="播放速度,默认为1", gt=0)
    delay: float = Field(default=0.0, description="延迟执行的时间(秒)", ge=0)


class SoundPlay(BaseModel):
    type: Literal["sound_play"]
    data: SoundPlayData


class SayData(BaseModel):
    text: List[str] = Field(description="要说的文本列表")
    speed: List[float] = Field(description="每段文本的播放速度列表, 代表1秒n字")
    font_size: int = Field(description="字体大小", default=config.SPEECH_SYNTHESIS.FONT_SIZE)
    font_color: str = Field(description="字体颜色, 16进制颜色码", default=config.SPEECH_SYNTHESIS.FONT_COLOR)
    font_path: str = Field(description="字体路径", default=config.SPEECH_SYNTHESIS.FONT_PATH)
    font_edge_color: str = Field(description="字体描边颜色, 16进制颜色码", default=config.SPEECH_SYNTHESIS.FONT_EDGE_COLOR)
    font_edge_width: int = Field(description="字体描边宽度", default=config.SPEECH_SYNTHESIS.FONT_EDGE_WIDTH)

class Say(BaseModel):
    """说话行为"""

    type: Literal["say"]
    data: SayData


class AnimationData(BaseModel):
    parameter: str = Field(description="VTS模型参数名称")
    from_value: Optional[float] = Field(
        default=None,
        alias="from",
        description="参数起始值",
    )
    target: float = Field(default=0, description="参数目标值")
    duration: float = Field(description="动画持续时间(秒)")
    delay: float = Field(default=0.0, description="延迟执行的时间(秒)")
    easing: str = Field(default="linear", description="缓动函数名称")


class Animation(BaseModel):
    """动画行为"""

    type: Literal["animation"]
    data: AnimationData


class EmotionData(BaseModel):
    name: Optional[str] = Field(
        default=None,
        description="表情文件名，如果为空则返回所有表情列表",
    )
    duration: float = Field(default=0.0, description="表情持续时间(秒), 小于等于0则未永久设置")
    delay: float = Field(default=0.0, description="延迟执行的时间(秒)")


class Emotion(BaseModel):
    """表情行为"""

    type: Literal["emotion"]
    data: EmotionData


class ExecuteData(BaseModel):
    loop: int = Field(default=0, description="循环次数，0表示不循环")


class Execute(BaseModel):
    """执行命令行为"""

    type: Literal["execute"]
    data: ExecuteData = Field(default_factory=ExecuteData)


Action = Union[Say, Animation, Emotion, Execute, SoundPlay]
