from typing import List, Literal, Optional, Union

from configs.config import config
from pydantic import BaseModel, Field


class SayData(BaseModel):
    text: List[str] = Field(description="要说的文本列表")
    speed: List[float] = Field(description="每段文本的速度列表")


class Say(BaseModel):
    """说话行为"""
    type: Literal["say"]
    data: SayData


class AnimationData(BaseModel):
    parameter: str = Field(description="VTS模型参数名称")
    from_value: Optional[float] = Field(default=None, alias="from", description="参数起始值")
    target: Optional[float] = Field(default=None, description="参数目标值")
    duration: float = Field(description="动画持续时间(秒)")
    delay: float = Field(default=0.0, description="延迟执行的时间(秒)")
    easing: str = Field(default="linear", description="缓动函数名称")

class Animation(BaseModel):
    """动画行为"""
    type: Literal["animation"]
    data: AnimationData

class EmotionData(BaseModel):
    name: Optional[str] = Field(default=None, description="表情文件名，如果为空则返回所有表情列表")
    duration: float = Field(default=0.0, description="表情持续时间(秒)")
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


Action = Union[Say, Animation, Emotion, Execute]

