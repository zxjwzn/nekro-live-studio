from pathlib import Path

import yaml
from pydantic import BaseModel, Field


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