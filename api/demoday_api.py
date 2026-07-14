"""Demoday 直播/项目相关接口封装。

对应 OpenAPI 文档 tag: "Exio home管理API_(WEB)"
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
    """获取 Demoday 正在讲解的项目。

    请求体字段说明（详见 OpenAPI: GetStartUpHomeReq）:
        pageNo:       页码，必填，最小值 1
        pageSize:     条数，必填，取值范围 [1, 100]
        projectName:  项目名称，选填，模糊搜索
        projectType:  项目分类，选填，取值 RECOMMENDED / MY_RATINGS / ALL
    该接口需要携带有效 Authorization Bearer Token，否则返回 2113 unauthorized access。
    """
    payload: dict = {"pageNo": page_no, "pageSize": page_size}
    if project_name is not None:
        payload["projectName"] = project_name
    if project_type is not None:
        payload["projectType"] = project_type
    return client.post(DEMODAY_LIVE_PATH, json=payload)
