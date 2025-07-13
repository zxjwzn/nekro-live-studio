from typing import List

from pydantic import BaseModel, Field

from ..configs.config import config


class Danmaku(BaseModel):
    """弹幕消息"""

    from_live_room: str = Field(default=config.BILIBILI_LIVE.LIVE_ROOM_ID, description="消息来源(房间号)")
    uid: str = Field(default="0", description="消息用户ID")
    username: str = Field(default="unknown", description="用户名")
    text: str = Field(default="", description="弹幕内容")
    time: int = Field(default=0, description="弹幕发送时间")
    url: List[str] = Field(default_factory=list, description="弹幕中的表情图片url列表")
    is_trigger: bool = Field(default=False, description="是否触发LLM (由ws客户端接收并处理)")
    is_system: bool = Field(default=False, description="是否为系统消息")
