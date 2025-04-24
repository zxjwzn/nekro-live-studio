from pydantic import BaseModel, Field
from typing import List, Optional

class Action(BaseModel):
    parameter: str
    from_value: Optional[float] = Field(None, alias="from")
    to: float
    duration: float = 1.0
    delay: float = 0.0
    easing: str = "linear"

class AnimationRequest(BaseModel):
    actions: List[Action]
    loop: int = 0 