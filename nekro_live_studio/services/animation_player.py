import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import json5
from pydantic import ValidationError
from simpleeval import SimpleEval

from ..schemas.actions import Action, Animation, AnimationData
from ..schemas.preformed_animation import (
    ActionTemplate,
    AnimationInfo,
    AnimationTemplate,
    Expression,
    RandomFloat,
    RandomInt,
)
from ..services.action_scheduler import action_scheduler
from ..utils.logger import logger

ANIMATIONS_DIR = Path("./data/resources/animations")
ANIMATIONS_DIR.mkdir(parents=True, exist_ok=True)


class AnimationPlayer:
    _instance: Optional["AnimationPlayer"] = None

    def __new__(cls) -> "AnimationPlayer":
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self._templates: Dict[str, AnimationTemplate] = {}
        self.load_animations()

    def load_animations(self):
        self._templates.clear()
        for file_path in ANIMATIONS_DIR.glob("*.jsonc"):
            try:
                with Path(file_path).open("r", encoding="utf-8") as f:
                    data = json5.load(f)
                template = AnimationTemplate.model_validate(data)
                if template.name in self._templates:
                    logger.warning(
                        f"动画名称冲突: '{template.name}' 在多个文件中定义. 将使用 {file_path} 中的版本.",
                    )
                self._templates[template.name] = template
            except (ValidationError, ValueError) as e:
                logger.error(f"解析动画文件失败 {file_path.name}: {e}")
            except Exception as e:
                logger.error(f"加载动画文件时发生未知错误 {file_path.name}: {e}")
        logger.info(f"成功加载 {len(self._templates)} 个动画模板.")

    def list_preformed_animations(self) -> List[AnimationInfo]:
        """返回所有动画的摘要信息列表"""
        self.load_animations()
        return [
            AnimationInfo(name=t.name, description=t.data.description, params=t.data.params) for t in self._templates.values()
        ]

    async def add_preformed_animation(
        self,
        name: str,
        params: Optional[Dict[str, Any]] = None,
        delay: float = 0.0,
    ) -> float:
        self.load_animations()
        template = self._templates.get(name)
        if not template:
            logger.error(f"未找到名为 '{name}' 的动画模板.")
            return 0.0

        max_completion_time = 0.0
        try:
            context = self._prepare_context(template, params)

            resolved_actions: List[Animation] = []
            for action_template in template.data.actions:
                final_action_data = self._resolve_action(
                    action_template,
                    context,
                    global_delay=delay,
                )
                resolved_actions.append(Animation(type="animation", data=final_action_data))

            for action in resolved_actions:
                completion_time = action_scheduler.add_action(action)
                if completion_time > max_completion_time:
                    max_completion_time = completion_time

        except (ValueError, KeyError) as e:
            logger.error(f"执行动画 '{name}' 失败: {e}", exc_info=True)
            return 0.0
        
        return max_completion_time

    def _prepare_context(self, template: AnimationTemplate, user_params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        context: Dict[str, Any] = {}
        user_params = user_params or {}

        # 1. 处理外部参数
        for param_def in template.data.params:
            if param_def.name in user_params:
                # TODO: 添加类型校验
                context[param_def.name] = user_params[param_def.name]
            elif param_def.default is not None:
                context[param_def.name] = param_def.default
            else:
                raise ValueError(f"缺少必需的参数: '{param_def.name}'")

        # 2. 处理内部变量
        for var_name, var_value in template.data.variables.items():
            context[var_name] = self._evaluate_value(var_value, context)

        return context

    def _resolve_action(
        self, action_template: ActionTemplate, context: Dict[str, Any], global_delay: float,
    ) -> AnimationData:
        target = self._evaluate_value(action_template.to, context)
        duration = self._evaluate_value(action_template.duration, context)
        action_delay = self._evaluate_value(action_template.delay, context)

        from_value = None
        if action_template.from_value is not None:
            from_value = self._evaluate_value(action_template.from_value, context)

        return AnimationData(
            parameter=action_template.parameter,
            from_value=float(from_value) if from_value is not None else None,
            target=float(target),
            duration=float(duration),
            delay=float(action_delay) + global_delay,
            easing=action_template.easing,
            priority=3,
        )

    def _evaluate_value(
        self,
        value: Union[float, str, Expression, RandomFloat, RandomInt],
        context: Dict[str, Any],
    ) -> Union[float, int, str]:
        if isinstance(value, (float, int, str)):
            return value
        if isinstance(value, RandomFloat):
            min_val, max_val = value.random_float
            return random.uniform(min_val, max_val)
        if isinstance(value, RandomInt):
            min_val, max_val = value.random_int
            return random.randint(min_val, max_val)
        if isinstance(value, Expression):
            evaluator = SimpleEval(names=context)
            return evaluator.eval(value.expr)
        raise TypeError(f"不支持的值类型: {type(value)}")


animation_player = AnimationPlayer()
