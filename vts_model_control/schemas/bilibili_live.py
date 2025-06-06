from typing import List, Optional, Union

from configs.config import config
from pydantic import BaseModel, Field


class Danmaku(BaseModel):
    from_live_room: str = Field(default=config.BILIBILI_CONFIGS.LIVE_ROOM_ID, description="消息来源(房间号)")
    uid: str = Field(default="0", description="消息用户ID")
    username: str = Field(default="unknown", description="用户名")
    text: str = Field(default="", description="弹幕内容")
    time: int = Field(default=0, description="弹幕发送时间")
    url: List[str] = Field(default_factory=list, description="弹幕中的表情图片url列表")
    is_trigget: bool = Field(default=True, description="是否触发LLM (由ws客户端接收并处理)")
    is_system: bool = Field(default=False, description="是否作为system身份发送 (由ws客户端接收并处理)")