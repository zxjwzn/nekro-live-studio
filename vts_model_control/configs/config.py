from pydantic import BaseModel, Field
from pathlib import Path

class ApiConfig(BaseModel):
    """API配置"""
    enabled: bool = Field(default=True, description="是否启用API")
    host: str = Field(default="0.0.0.0", description="API主机地址")
    port: int = Field(default=8080, description="API端口号")
    timeout: float = Field(default=5.0, description="超时时间，超过指定时间无API调用则恢复空闲动画")

class PluginConfig(BaseModel):
    """插件基本配置"""
    plugin_name: str = "vts模型控制插件"
    plugin_developer: str = "Zaxpris"
    default_vts_endpoint: str = "ws://localhost:8002"
    debug_mode: bool = Field(default=False, description="是否启用调试模式")
    restore_duration: float = Field(default=3.0, description="恢复参数过渡时间（秒）")
    cleanup_timeout: float = Field(default=5.0, description="清理操作超时时间（秒）")
    pre_animation_duration: float = Field(default=0.5, description="动画前置过渡时间（秒）")


class BlinkConfig(BaseModel):
    """眨眼配置"""
    enabled: bool = Field(default=True, description="是否启用眨眼效果")
    min_interval: float = Field(default=2.0, description="两次眨眼之间的最小间隔时间（秒）")
    max_interval: float = Field(default=4.0, description="两次眨眼之间的最大间隔时间（秒）")
    close_duration: float = Field(default=0.15, description="闭眼动画持续时间（秒）")
    open_duration: float = Field(default=0.3, description="睁眼动画持续时间（秒）")
    closed_hold: float = Field(default=0.05, description="眼睛闭合状态的保持时间（秒）")
    left_parameter: str = Field(default="EyeOpenLeft", description="眨眼控制的参数名")
    right_parameter: str = Field(default="EyeOpenRight", description="眨眼控制的参数名")
    min_value: float = Field(default=0.0, description="眨眼最小值（闭眼）")
    max_value: float = Field(default=1, description="眨眼最大值（睁眼）")


class BreathingConfig(BaseModel):
    """呼吸配置"""
    enabled: bool = Field(default=True, description="是否启用呼吸效果")
    min_value: float = Field(default=-3.0, description="呼吸参数最小值（呼气）")
    max_value: float = Field(default=3.0, description="呼吸参数最大值（吸气）")
    inhale_duration: float = Field(default=1.0, description="吸气持续时间（秒）")
    exhale_duration: float = Field(default=2.0, description="呼气持续时间（秒）")
    parameter: str = Field(default="FaceAngleY", description="呼吸控制的参数名")


class BodySwingConfig(BaseModel):
    """身体摇摆配置"""
    enabled: bool = Field(default=True, description="是否启用身体摇摆效果")
    x_min: float = Field(default=-10.0, description="身体左右摇摆最小位置（左侧）")
    x_max: float = Field(default=15.0, description="身体左右摇摆最大位置（右侧）")
    z_min: float = Field(default=-10.0, description="上肢旋转最小位置（下方）")
    z_max: float = Field(default=15.0, description="上肢旋转最大位置（上方）")
    min_duration: float = Field(default=2.0, description="摇摆最短持续时间（秒）")
    max_duration: float = Field(default=8.0, description="摇摆最长持续时间（秒）")
    x_parameter: str = Field(default="FaceAngleX", description="身体左右摇摆控制的参数名")
    z_parameter: str = Field(default="FaceAngleZ", description="上肢旋转控制的参数名")


class EyeFollowConfig(BaseModel):
    """眼睛跟随配置"""
    enabled: bool = Field(default=True, description="是否启用眼睛跟随身体摇摆")
    x_min_range: float = Field(default=-1.0, description="眼睛左右移动最小值（左侧）")
    x_max_range: float = Field(default=1.0, description="眼睛左右移动最大值（右侧）")
    y_min_range: float = Field(default=-1.0, description="眼睛上下移动最小值（下方）")
    y_max_range: float = Field(default=1.0, description="眼睛上下移动最大值（上方）")
    left_x_parameter: str = Field(default="EyeLeftX", description="左眼水平移动参数")
    right_x_parameter: str = Field(default="EyeRightX", description="右眼水平移动参数")
    left_y_parameter: str = Field(default="EyeLeftY", description="左眼垂直移动参数")
    right_y_parameter: str = Field(default="EyeRightY", description="右眼垂直移动参数")


class MouthExpressionConfig(BaseModel):
    """嘴部表情配置"""
    enabled: bool = Field(default=True, description="是否启用嘴部表情变化")
    smile_min: float = Field(default=0.1, description="嘴角微笑最小值（不高兴）")
    smile_max: float = Field(default=0.7, description="嘴角微笑最大值（高兴）")
    open_min: float = Field(default=0.1, description="嘴巴开合最小值（闭合）")
    open_max: float = Field(default=0.7, description="嘴巴开合最大值（张开，可调小避免过度张嘴）")
    change_min_duration: float = Field(default=2.0, description="表情变化最短持续时间（秒）")
    change_max_duration: float = Field(default=7.0, description="表情变化最长持续时间（秒）")
    smile_parameter: str = Field(default="MouthSmile", description="嘴角微笑控制的参数名")
    open_parameter: str = Field(default="MouthOpen", description="嘴巴开合控制的参数名")


class VTSModelControlConfig(BaseModel):
    """VTS面部控制总配置"""
    plugin: PluginConfig = Field(default_factory=PluginConfig)
    blink: BlinkConfig = Field(default_factory=BlinkConfig)
    breathing: BreathingConfig = Field(default_factory=BreathingConfig)
    body_swing: BodySwingConfig = Field(default_factory=BodySwingConfig)
    eye_follow: EyeFollowConfig = Field(default_factory=EyeFollowConfig)
    mouth_expression: MouthExpressionConfig = Field(default_factory=MouthExpressionConfig)
    models: list[Path] = Field(default_factory=list, description="模型文件路径列表")
    api: ApiConfig = Field(default_factory=ApiConfig)

from pathlib import Path  # 确保 Path 可用
# 配置文件路径
CONFIG_FILE: Path = Path(__file__).parent / "config.json"

def load_config() -> VTSModelControlConfig:
    """显式加载配置：如果不存在则返回默认实例，但不自动写入文件。"""
    if CONFIG_FILE.exists():
        return VTSModelControlConfig.model_validate_json(CONFIG_FILE.read_text(encoding="utf-8"))
    return VTSModelControlConfig()

def save_config(cfg: VTSModelControlConfig) -> None:
    """将配置写入 config.json 文件。"""
    CONFIG_FILE.write_text(cfg.model_dump_json(indent=4), encoding="utf-8")

# 全局配置实例（加载时不会自动写入文件）
config: VTSModelControlConfig = load_config()

# 可以通过以下方式使用配置，例如：
# config.blink.ENABLED
# config.breathing.PARAMETER
