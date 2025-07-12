from pydantic import Field

from ..configs.base import ConfigBase


class ControllerConfig(ConfigBase):
    ENABLED: bool = Field(default=True, description="是否启用控制器")