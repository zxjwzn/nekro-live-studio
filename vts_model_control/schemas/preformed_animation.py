from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class ParamDef(BaseModel):
    """动画模板中外部参数的定义"""

    name: str
    description: Optional[str] = None
    type: Literal["float", "int", "str"] = "float"
    default: Optional[Union[float, int, str]] = None


class RandomFloat(BaseModel):
    random_float: List[float] = Field(..., min_length=2, max_length=2)


class RandomInt(BaseModel):
    random_int: List[int] = Field(..., min_length=2, max_length=2)


class Expression(BaseModel):
    expr: str


class ActionTemplate(BaseModel):
    """动画模板中的单个动作"""

    parameter: str
    from_value: Optional[Union[float, int, Expression, RandomFloat, RandomInt]] = None
    to: Union[float, int, Expression, RandomFloat, RandomInt]
    duration: Union[float, Expression, RandomFloat]
    easing: str = "linear"
    delay: Union[float, Expression, RandomFloat] = 0.0


class AnimationTemplateData(BaseModel):
    """动画模板的 'data' 部分"""

    description: Optional[str] = None
    params: List[ParamDef] = Field(default_factory=list)
    variables: Dict[
        str, Union[float, int, str, Expression, RandomFloat, RandomInt],
    ] = Field(
        default_factory=dict,
    )
    actions: List[ActionTemplate]


class AnimationTemplate(BaseModel):
    """完整的动画模板定义"""

    name: str
    type: Literal["animation"]
    data: AnimationTemplateData


class AnimationInfo(BaseModel):
    """用于列表显示的动画信息"""

    name: str
    description: Optional[str] = None
    params: List[ParamDef] = Field(default_factory=list) 