"""Demoday 直播/项目相关接口封装。

对应 OpenAPI 文档 tag: \"Exio home管理API_(WEB)\"
参考: openapi/wali_openapi.json -> paths./exio/demoday/live
"""
from __future__ import annotations

import requests

from api.client import ApiClient

DEMODAY_LIVE_PATH = "/exio/demoday/live"


def get_demoday_live(
    client: ApiClient,
    page_no: int = 1,
    page_size: int = 10,
    project_name: str | None = None,
    project_type: str | None = None,
) -> requests.Response:
    """获取 Demoday 正在讲解的项目。需要有效 Authorization，否则 2113。"""
    payload: dict = {"pageNo": page_no, "pageSize": page_size}
    if project_name is not None:
        payload["projectName"] = project_name
    if project_type is not None:
        payload["projectType"] = project_type
    return client.post(DEMODAY_LIVE_PATH, json=payload)
