"""
章节输出 JSON Schema — 供 Agent 结构化输出使用

从 output_schema.py 的 dataclass 定义自动生成 OpenAI response_format
兼容的 JSON Schema，也用于 system prompt 中描述输出要求。
"""
import json
from dataclasses import fields as dc_fields
from typing import List, Dict, Any, Optional, get_type_hints

# Python type → JSON Schema type 映射
_TYPE_MAP = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
}


def dataclass_to_json_schema(cls) -> Dict[str, Any]:
    """
    将 dataclass 转为 JSON Schema

    Args:
        cls: dataclass 类（如 Ch01Output）

    Returns:
        JSON Schema dict
    """
    properties = {}
    required = []

    for f in dc_fields(cls):
        type_name = f.type.__name__ if hasattr(f.type, "__name__") else str(f.type)

        # 处理 List[str] 等泛型
        if "List" in type_name or "list" in type_name:
            prop = {"type": "array", "items": {"type": "string"}}
        elif "Dict" in type_name or "dict" in type_name:
            prop = {"type": "object"}
        elif "Optional" in type_name:
            # Optional[X] → nullable X
            inner = type_name.replace("Optional[", "").rstrip("]")
            json_type = _TYPE_MAP.get(inner, "string")
            prop = {"type": json_type}
        else:
            json_type = _TYPE_MAP.get(type_name, "string")
            prop = {"type": json_type}

        # 从 docstring 或 field 注释提取描述
        properties[f.name] = prop

    return {
        "type": "object",
        "properties": properties,
        "required": list(properties.keys()),
    }


def schema_to_prompt_description(cls) -> str:
    """
    将 dataclass 的字段描述转为 prompt 中的输出要求文本

    Returns:
        Markdown 格式的字段说明
    """
    lines = []
    for f in dc_fields(cls):
        type_name = f.type.__name__ if hasattr(f.type, "__name__") else str(f.type)

        # 从默认值推断说明
        default_hint = ""
        if f.default is not None and f.default != "":
            if isinstance(f.default, str) and f.default:
                default_hint = f"  // {f.default}"
            elif isinstance(f.default, bool):
                default_hint = f"  // true/false"

        lines.append(f'  "{f.name}": {type_name}{default_hint}')

    return "```json\n{\n" + ",\n".join(lines) + "\n}\n```"


def build_synthesis_schema(synthesis_fields: List[str]) -> Dict[str, Any]:
    """
    从 synthesis_fields 配置生成综合研判的 JSON Schema

    Args:
        synthesis_fields: 策略配置中的 synthesis_fields 列表
            如 ["流派判定: 纯硬收息 / 价值发现 / 烟蒂股 / 关联方资源", ...]
    """
    properties = {}
    for field_str in synthesis_fields:
        # "流派判定: 纯硬收息 / ..." → key="流派判定", desc="纯硬收息 / ..."
        parts = field_str.split(":", 1)
        key = parts[0].strip().replace("（强制）", "").replace("(强制)", "")
        desc = parts[1].strip() if len(parts) > 1 else ""

        # 简单推断类型
        if "0-100" in desc or "倍数" in desc or "边际" in desc:
            prop = {"type": "number", "description": desc}
        elif "/" in desc:
            options = [o.strip() for o in desc.split("/")]
            prop = {"type": "string", "enum": options, "description": desc}
        else:
            prop = {"type": "string", "description": desc}

        # key 转为合法 JSON key
        safe_key = key.replace(" ", "_")
        properties[safe_key] = prop

    return {
        "type": "object",
        "properties": properties,
        "required": list(properties.keys()),
    }
