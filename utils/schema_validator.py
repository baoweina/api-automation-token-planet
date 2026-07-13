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
    """递归展开 $ref，处理循环引用（遇到环就用空 schema 截断）。"""
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

    因为实测发现：1) 文档几乎没标 nullable，但实际业务响应对象/数组字段经常合法返回 null；
    2) 后端对大整数（int64）字段实际以字符串形式返回（避免 JS 精度丢失）。
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
