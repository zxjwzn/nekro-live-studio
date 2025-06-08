from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from .base import ConfigBase

CONFIG_PATH = Path("./data") / "configs" / "vts_model_control.yaml"
CONFIG_DIR = Path("./data") / "configs"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


class ApiConfig(ConfigBase):
    """API配置"""

    HOST: str = Field(default="0.0.0.0", description="API主机地址")
    PORT: int = Field(default=8080, description="API端口号")
    TIMEOUT: float = Field(
        default=5.0,
        description="超时时间，超过指定时间无API调用则恢复空闲动画",
    )


class PluginConfig(ConfigBase):
    """插件基本配置"""

    PLUGIN_NAME: str = "vts模型控制插件"
    PLUGIN_DEVELOPER: str = "Zaxpris"
    VTS_ENDPOINT: str = "ws://localhost:8001"
    AUTHENTICATION_TOKEN: str = ""
    RESTORE_DURATION: float = Field(default=3.0, description="恢复参数过渡时间（秒）")
    CLEANUP_TIMEOUT: float = Field(default=5.0, description="清理操作超时时间（秒）")
    PRE_ANIMATION_DURATION: float = Field(
        default=0.5,
        description="动画前置过渡时间（秒）",
    )
    EXPRESSION_FADE_TIME: float = Field(
        default=0.25,
        description="表情淡入淡出时间（秒），VTube Studio API默认0.5s",
    )


class SpeechSynthesisConfig(ConfigBase):
    """RPG风格语音合成配置"""

    ENABLED: bool = Field(default=True, description="是否启用RPG风格语音播放")
    TEXT_PER_SECOND_RATE: float = Field(default=5.0, description="每秒播放的字数 (播放速率)")
    AUDIO_FILE_PATH: str = Field(
        default="vocal_.wav",
        description="用于播放的音频文件路径",
    )
    VOLUME: float = Field(default=0.5, ge=0.0, le=1.0, description="播放音量 (范围 0.0 到 1.0)")
    FONT_PATH: str = Field(default="data/resources/fonts/JinNianYeYaoJiaYouYa.ttf", description="字体路径")
    FONT_COLOR: str = Field(default="#ffffff", description="字体颜色, 16进制颜色码")
    FONT_EDGE_COLOR: str = Field(default="#000000", description="字体描边颜色, 16进制颜色码")
    FONT_EDGE_WIDTH: int = Field(default=1, description="字体描边宽度")
    FONT_SIZE: int = Field(default=50, description="字体大小")


class BilibiliConfigs(ConfigBase):
    """Bilibili直播配置"""

    LIVE_ROOM_ID: str = Field(default="0", description="Bilibili直播房间ID")
    TRIGGER_COUNT: int = Field(default=10, description="触发LLM的弹幕/消息条数")
    TRIGGER_TIME: float = Field(default=10.0, description="触发LLM的最大等待时间 (秒)")
    SESSDATA: str = Field(default="", description="Bilibili直播 sessdata")
    BILI_JCT: str = Field(default="", description="Bilibili直播 bili_jct")
    BUVID3: str = Field(default="", description="Bilibili直播 buvid3")
    DEDEUSERID: str = Field(default="", description="Bilibili直播 dedeuserid 可不填")
    AC_TIME_VALUE: str = Field(default="", description="Bilibili直播 ac_time_value 可不填")


class VTSModelControlConfig(ConfigBase):
    """VTS面部控制总配置"""

    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        title="应用日志级别",
    )
    PLUGIN: PluginConfig = Field(default_factory=PluginConfig)
    SPEECH_SYNTHESIS: SpeechSynthesisConfig = Field(default_factory=SpeechSynthesisConfig)
    MODELS: list[Path] = Field(default_factory=list, description="模型文件路径列表")
    API: ApiConfig = Field(default_factory=ApiConfig)
    BILIBILI_CONFIGS: BilibiliConfigs = Field(default_factory=BilibiliConfigs)


try:
    config = VTSModelControlConfig.load_config(file_path=CONFIG_PATH)
except Exception as e:
    print(f"VTS Model Controll 配置文件加载失败: {e} | 请检查配置文件是否符合语法要求")
    print("应用将退出...")
    exit(1)
config.dump_config(file_path=CONFIG_PATH)


def save_config():
    """保存配置"""
    global config
    config.dump_config(file_path=CONFIG_PATH)


def reload_config():
    """重新加载配置文件"""
    global config

    new_config = PluginConfig.load_config(file_path=CONFIG_PATH)
    # 更新配置字段
    for field_name in PluginConfig.model_fields:
        value = getattr(new_config, field_name)
        setattr(config, field_name, value)
