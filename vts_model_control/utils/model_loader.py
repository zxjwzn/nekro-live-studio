import json
from pathlib import Path
from typing import Dict, Tuple, Optional
from configs.config import config
from utils.logger import logger
from pydantic import BaseModel

class ParameterMapping(BaseModel):
    output_range_lower: float
    output_range_upper: float
    output_live2d: str

# 模型参数注册表: {模型名字: {输入参数名: (输出下限, 输出上限, Live2D 参数名)}}

class ModelLoader():
    _model_registry: Dict[str, Dict[str, ParameterMapping]] = {}

    # 初始化模型注册表
    def __init__(self) -> None:
        for model_path in config.models:
            path = Path(model_path)
            try:
                if not path.is_file():
                    continue
                data = json.loads(path.read_text(encoding="utf-8"))
                model_name = data.get("Name")
                logger.info(f"加载模型: {model_name}")
                param_list = data.get("ParameterSettings", [])
                mapping: Dict[str, ParameterMapping] = {}
                for p in param_list:
                    input_name = p.get("Input")
                    mapping[input_name] = ParameterMapping(
                        output_range_lower=p.get("OutputRangeLower"),
                        output_range_upper=p.get("OutputRangeUpper"),
                        output_live2d=p.get("OutputLive2D"),
                    )
                if model_name:
                    self._model_registry[model_name] = mapping
            except Exception:
                continue

    def get_parameter_mapping(self, model_name: str, input_name: str) -> Optional[ParameterMapping]:
        """
        根据模型名和输入参数名获取 ParameterMapping 结构，包括输出范围和 Live2D 参数名称。
        :param model_name: vtube.json 文件中的 Name 字段
        :param input_name: ParameterSettings 中的 Input 字段
        :return: ParameterMapping 实例，若未找到则返回 None
        """
        return self._model_registry.get(model_name, {}).get(input_name) 