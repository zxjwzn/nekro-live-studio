from typing import Dict

from pydantic import Field

from configs.base import ConfigBase


class AudioDescriptionFile(ConfigBase):
    """音效描述文件模型"""

    descriptions: Dict[str, str] = Field(default_factory=dict, description="音效文件名到描述的映射")
