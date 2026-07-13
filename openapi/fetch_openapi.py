"""拉取最新的 OpenAPI 文档并覆盖本地缓存文件。

用法:
    python openapi/fetch_openapi.py
"""
from __future__ import annotations

import json
from pathlib import Path

import requests

OPENAPI_URL = "https://manager-test.wali.network/app/v3/api-docs"
OUTPUT_FILE = Path(__file__).parent / "wali_openapi.json"


def main() -> None:
    resp = requests.get(OPENAPI_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    OUTPUT_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"已更新 OpenAPI 文档: {OUTPUT_FILE} (paths: {len(data.get('paths', {}))})")


if __name__ == "__main__":
    main()
