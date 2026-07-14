"""基于本地缓存的 OpenAPI 文档，对接口响应做 JSON Schema 校验。

用法::

    from utils.schema_validator import validate_schema
    validate_schema(resp.json(), "ResultUserRoleInfoDto")
"""
from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any

import jsonschema

OPENAPI_FILE = Path(__file__).resolve().parent.parent / "openapi" / "wali_openapi.json"


@functools.lru_cache(maxsize=1)
def _load_openapi() -> dict:
    return json.loads(OPENAPI_FILE.read_text(encoding="utf-8"))


def _resolve_refs(node: Any, schemas: dict, _stack: frozenset[str] = frozenset()) -> Any:
    """递归展开 $ref，生成 jsonschema 库可直接使用的完整 schema。

    这份文档里业务模型之间存在循环引用（A 引用 B、B 又引用 A），
    展开时用 _stack 记录当前正在展开的 schema 名称，遇到环就用一个
    不做限制的空 schema（{}）截断，避免无限递归；对我们要校验的
    "结构/枚举值对不对"这个目标来说，环路深处的字段不校验也无妨。
    """
    if isinstance(node, dict):
        if "$ref" in node:
            ref_name = node["$ref"].split("/")[-1]
            if ref_name in _stack:
                return {}
            return _resolve_refs(schemas[ref_name], schemas, _stack | {ref_name})
        return {k: _resolve_refs(v, schemas, _stack) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve_refs(item, schemas, _stack) for item in node]
    return node


def _allow_null(node: Any) -> Any:
    """把每个字段的 type 都放宽为可为 null，并容忍 int64 字段被序列化成字符串。

    这份 OpenAPI 文档（Swagger 从 Java/Spring 生成）里有两个跟实际响应不一致的地方：

    1. 几乎没有标注 nullable，但实际业务响应里对象/数组字段经常合法地返回 null
       （比如未申请过创业者身份时 exioStartupApplication 为 null）。
    2. 文档写的是 type=integer/format=int64，但实测发现像 loginId 这种大整数，
       后端实际是以字符串形式返回的（典型 Jackson 序列化策略，避免超出
       JS Number 安全整数范围导致前端精度丢失）。这不是我们要抓的 bug，
       是后端故意的设计，所以这里也一并放宽容忍。

    为了让 schema 校验能聚焦在"字段类型/枚举值对不对"这个目标，而不是被
    文档没写全/文档与实际序列化方式不一致坑掉，这里统一放宽。
    """
    if isinstance(node, dict):
        node = {k: _allow_null(v) for k, v in node.items()}
        if "type" in node:
            t = node["type"]
            types = t if isinstance(t, list) else [t]
            if node.get("format") == "int64" and "string" not in types:
                types = [*types, "string"]
            if "null" not in types:
                types = [*types, "null"]
            node["type"] = types
        return node
    if isinstance(node, list):
        return [_allow_null(item) for item in node]
    return node


def get_schema(schema_name: str) -> dict:
    doc = _load_openapi()
    schemas = doc["components"]["schemas"]
    resolved = _resolve_refs(schemas[schema_name], schemas, frozenset({schema_name}))
    return _allow_null(resolved)


def validate_schema(instance: Any, schema_name: str) -> None:
    """校验 instance 是否符合 OpenAPI 文档中 components.schemas[schema_name] 的定义。"""
    schema = get_schema(schema_name)
    jsonschema.validate(instance=instance, schema=schema)
