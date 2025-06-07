from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

CONFIG_PATH = Path("./data") / "configs" / "vts_model_control.yaml"
CONFIG_DIR = Path("./data") / "configs"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


class ConfigBase(BaseModel):
    @classmethod
    def load_config(cls, file_path: Path):
        """加载配置文件"""
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            return cls()
        content: str = file_path.read_text(encoding="utf-8")
        if file_path.suffix == ".json":
            return cls.model_validate_json(content)
        if file_path.suffix in [".yaml", ".yml"]:
            return cls.model_validate(yaml.safe_load(content))
        raise ValueError(f"Unsupported file type: {file_path}")

    def dump_config(self, file_path: Path) -> None:
        """保存配置文件"""
        if file_path.suffix == ".json":
            file_path.write_text(self.model_dump_json(), encoding="utf-8")
        elif file_path.suffix in [".yaml", ".yml"]:
            yaml_str = yaml.dump(
                data=self.model_dump(),
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
            file_path.write_text(yaml_str, encoding="utf-8")
        else:
            raise ValueError(f"Unsupported file type: {file_path}")

    @classmethod
    def get_field_title(cls, field_name: str) -> str:
        """获取字段的中文标题"""
        return cls.model_fields.get(field_name).title  # type: ignore

    @classmethod
    def get_field_placeholder(cls, field_name: str) -> str:
        """获取字段的占位符文本"""
        field = cls.model_fields.get(field_name)
        if field and hasattr(field, "json_schema_extra") and isinstance(field.json_schema_extra, dict):
            placeholder = field.json_schema_extra.get("placeholder")
            return str(placeholder) if placeholder is not None else ""
        return ""


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
    VTS_ENDPOINT: str = "ws://localhost:8002"
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


class BlinkConfig(ConfigBase):
    """眨眼配置"""

    ENABLED: bool = Field(default=True, description="是否启用眨眼效果")
    MIN_INTERVAL: float = Field(
        default=2.0,
        description="两次眨眼之间的最小间隔时间（秒）",
    )
    MAX_INTERVAL: float = Field(
        default=4.0,
        description="两次眨眼之间的最大间隔时间（秒）",
    )
    CLOSE_DURATION: float = Field(default=0.15, description="闭眼动画持续时间（秒）")
    OPEN_DURATION: float = Field(default=0.3, description="睁眼动画持续时间（秒）")
    CLOSED_HOLD: float = Field(default=0.05, description="眼睛闭合状态的保持时间（秒）")
    LEFT_PARAMETER: str = Field(default="EyeOpenLeft", description="眨眼控制的参数名")
    RIGHT_PARAMETER: str = Field(default="EyeOpenRight", description="眨眼控制的参数名")
    MIN_VALUE: float = Field(default=0.0, description="眨眼最小值（闭眼）")
    MAX_VALUE: float = Field(default=1, description="眨眼最大值（睁眼）")


class BreathingConfig(ConfigBase):
    """呼吸配置"""

    ENABLED: bool = Field(default=True, description="是否启用呼吸效果")
    MIN_VALUE: float = Field(default=-3.0, description="呼吸参数最小值（呼气）")
    MAX_VALUE: float = Field(default=3.0, description="呼吸参数最大值（吸气）")
    INHALE_DURATION: float = Field(default=1.0, description="吸气持续时间（秒）")
    EXHALE_DURATION: float = Field(default=2.0, description="呼气持续时间（秒）")
    PARAMETER: str = Field(default="FaceAngleY", description="呼吸控制的参数名")


class BodySwingConfig(ConfigBase):
    """身体摇摆配置"""

    ENABLED: bool = Field(default=True, description="是否启用身体摇摆效果")
    X_MIN: float = Field(default=-10.0, description="身体左右摇摆最小位置（左侧）")
    X_MAX: float = Field(default=15.0, description="身体左右摇摆最大位置（右侧）")
    Z_MIN: float = Field(default=-10.0, description="上肢旋转最小位置（下方）")
    Z_MAX: float = Field(default=15.0, description="上肢旋转最大位置（上方）")
    MIN_DURATION: float = Field(default=2.0, description="摇摆最短持续时间（秒）")
    MAX_DURATION: float = Field(default=8.0, description="摇摆最长持续时间（秒）")
    X_PARAMETER: str = Field(
        default="FaceAngleX",
        description="身体左右摇摆控制的参数名",
    )
    Z_PARAMETER: str = Field(default="FaceAngleZ", description="上肢旋转控制的参数名")


class EyeFollowConfig(ConfigBase):
    """眼睛跟随配置"""

    ENABLED: bool = Field(default=True, description="是否启用眼睛跟随身体摇摆")
    X_MIN_RANGE: float = Field(default=-1.0, description="眼睛左右移动最小值（左侧）")
    X_MAX_RANGE: float = Field(default=1.0, description="眼睛左右移动最大值（右侧）")
    Y_MIN_RANGE: float = Field(default=-1.0, description="眼睛上下移动最小值（下方）")
    Y_MAX_RANGE: float = Field(default=1.0, description="眼睛上下移动最大值（上方）")
    LEFT_X_PARAMETER: str = Field(default="EyeLeftX", description="左眼水平移动参数")
    RIGHT_X_PARAMETER: str = Field(default="EyeRightX", description="右眼水平移动参数")
    LEFT_Y_PARAMETER: str = Field(default="EyeLeftY", description="左眼垂直移动参数")
    RIGHT_Y_PARAMETER: str = Field(default="EyeRightY", description="右眼垂直移动参数")


class MouthExpressionConfig(ConfigBase):
    """嘴部表情配置"""

    ENABLED: bool = Field(default=True, description="是否启用嘴部表情变化")
    SMILE_MIN: float = Field(default=0.1, description="嘴角微笑最小值（不高兴）")
    SMILE_MAX: float = Field(default=0.7, description="嘴角微笑最大值（高兴）")
    OPEN_MIN: float = Field(default=0.1, description="嘴巴开合最小值（闭合）")
    OPEN_MAX: float = Field(default=0.7, description="嘴巴开合最大值（张开，可调小避免过度张嘴）")
    CHANGE_MIN_DURATION: float = Field(default=2.0, description="表情变化最短持续时间（秒）")
    CHANGE_MAX_DURATION: float = Field(default=7.0, description="表情变化最长持续时间（秒）")
    SMILE_PARAMETER: str = Field(default="MouthSmile", description="嘴角微笑控制的参数名")
    OPEN_PARAMETER: str = Field(default="MouthOpen", description="嘴巴开合控制的参数名")


class SpeechSynthesisConfig(ConfigBase):
    """RPG风格语音合成配置"""

    ENABLED: bool = Field(default=True, description="是否启用RPG风格语音播放")
    TEXT_PER_SECOND_RATE: float = Field(default=5.0, description="每秒播放的字数 (播放速率)")
    AUDIO_FILE_PATH: str = Field(
        default="D:\\\\QQbot\\\\live2d\\\\vts_face_control_plugin\\\\vts_model_control\\\\resources\\\\audios\\\\vocal_.mp3",
        description="用于播放的音频文件路径",
    )
    VOLUME: float = Field(default=0.5, ge=0.0, le=1.0, description="播放音量 (范围 0.0 到 1.0)")


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
    BLINK: BlinkConfig = Field(default_factory=BlinkConfig)
    BREATHING: BreathingConfig = Field(default_factory=BreathingConfig)
    BODY_SWING: BodySwingConfig = Field(default_factory=BodySwingConfig)
    EYE_FOLLOW: EyeFollowConfig = Field(default_factory=EyeFollowConfig)
    MOUTH_EXPRESSION: MouthExpressionConfig = Field(default_factory=MouthExpressionConfig)
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
