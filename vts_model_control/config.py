from pydantic import BaseModel, Field


class PluginConfig(BaseModel):
    """插件基本配置"""
    PLUGIN_NAME: str = "vts模型控制插件"
    PLUGIN_DEVELOPER: str = "Zaxpris"
    DEFAULT_VTS_ENDPOINT: str = "ws://localhost:8002"
    DEBUG_MODE: bool = Field(default=False, description="是否启用调试模式")
    RESTORE_DURATION: float = Field(default=1.0, description="恢复参数过渡时间（秒）")
    CLEANUP_TIMEOUT: float = Field(default=5.0, description="清理操作超时时间（秒）")


class BlinkConfig(BaseModel):
    """眨眼配置"""
    ENABLED: bool = Field(default=True, description="是否启用眨眼效果")
    MIN_INTERVAL: float = Field(default=2.0, description="两次眨眼之间的最小间隔时间（秒）")
    MAX_INTERVAL: float = Field(default=4.0, description="两次眨眼之间的最大间隔时间（秒）")
    CLOSE_DURATION: float = Field(default=0.15, description="闭眼动画持续时间（秒）")
    OPEN_DURATION: float = Field(default=0.3, description="睁眼动画持续时间（秒）")
    CLOSED_HOLD: float = Field(default=0.05, description="眼睛闭合状态的保持时间（秒）")
    LEFT_PARAMETER: str = Field(default="EyeOpenLeft", description="眨眼控制的参数名")
    RIGHT_PARAMETER: str = Field(default="EyeOpenRight", description="眨眼控制的参数名")
    MIN_VALUE: float = Field(default=0.0, description="眨眼最小值（闭眼）")
    MAX_VALUE: float = Field(default=0.5, description="眨眼最大值（睁眼）")


class BreathingConfig(BaseModel):
    """呼吸配置"""
    ENABLED: bool = Field(default=True, description="是否启用呼吸效果")
    MIN_VALUE: float = Field(default=-3.0, description="呼吸参数最小值（呼气）")
    MAX_VALUE: float = Field(default=3.0, description="呼吸参数最大值（吸气）")
    INHALE_DURATION: float = Field(default=2.0, description="吸气持续时间（秒）")
    EXHALE_DURATION: float = Field(default=2.5, description="呼气持续时间（秒）")
    PARAMETER: str = Field(default="FaceAngleY", description="呼吸控制的参数名")


class BodySwingConfig(BaseModel):
    """身体摇摆配置"""
    ENABLED: bool = Field(default=True, description="是否启用身体摇摆效果")
    X_MIN: float = Field(default=-10.0, description="身体左右摇摆最小位置（左侧）")
    X_MAX: float = Field(default=15.0, description="身体左右摇摆最大位置（右侧）")
    Z_MIN: float = Field(default=-10.0, description="上肢旋转最小位置（下方）")
    Z_MAX: float = Field(default=15.0, description="上肢旋转最大位置（上方）")
    MIN_DURATION: float = Field(default=2.0, description="摇摆最短持续时间（秒）")
    MAX_DURATION: float = Field(default=8.0, description="摇摆最长持续时间（秒）")
    X_PARAMETER: str = Field(default="FaceAngleX", description="身体左右摇摆控制的参数名")
    Z_PARAMETER: str = Field(default="FaceAngleZ", description="上肢旋转控制的参数名")


class EyeFollowConfig(BaseModel):
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


class MouthExpressionConfig(BaseModel):
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


class VTSModelControlConfig(BaseModel):
    """VTS面部控制总配置"""
    plugin: PluginConfig = Field(default_factory=PluginConfig)
    blink: BlinkConfig = Field(default_factory=BlinkConfig)
    breathing: BreathingConfig = Field(default_factory=BreathingConfig)
    body_swing: BodySwingConfig = Field(default_factory=BodySwingConfig)
    eye_follow: EyeFollowConfig = Field(default_factory=EyeFollowConfig)
    mouth_expression: MouthExpressionConfig = Field(default_factory=MouthExpressionConfig)


# 创建默认配置实例
config = VTSModelControlConfig()

# 可以通过以下方式使用配置，例如：
# config.blink.ENABLED
# config.breathing.PARAMETER
