"""Startup（初创企业项目）相关接口封装。

对应 OpenAPI 文档 tag: "Exio home管理API_(WEB)"
参考: openapi/wali_openapi.json -> paths./exio/startup/vote-record/list
"""
from __future__ import annotations

import requests

from api.client import ApiClient

VOTE_RECORD_LIST_PATH = "/exio/startup/vote-record/list"


def get_investor_vote_record_page(
    client: ApiClient,
    page_no: int = 1,
    page_size: int = 10,
    startup_id: int | None = 0,
    season_id: int | None = None,
) -> requests.Response:
    """获取投资方对某个项目的认筹记录分页。

    请求体字段说明（详见 OpenAPI: GetInvestorVoteRecordReq）:
        pageNo:     页码，必填，最小值 1，默认 1
        pageSize:   条数，必填，取值范围 [1, 100]，默认 10
        startupId:  项目ID，必填（不能为空，否则返回 1100 参数校验错误）
        seasonId:   赛季ID，选填；不传则查询最新赛季，传 0 则查所有赛季

    该接口需要携带有效 Authorization Bearer Token。已实测确认：
    - 必填参数缺失/越界（如缺 startupId、pageSize 超出 [1,100]）会先被参数校验拦截，
      返回 1100，即使未登录也是如此（参数校验优先于鉴权检查）。
    - 参数合法但未携带 Token 时，返回 2113 unauthorized access。
    - 携带无效/伪造 Token 时，返回 2110 "Your login information has expired.
      Please log in again"（注意：这跟 /exio/demoday/live 对无效 Token 的表现不同，
      不要想当然地认为所有接口对无效 Token 都返回同一个错误码）。
    """
    payload: dict = {"pageNo": page_no, "pageSize": page_size}
    if startup_id is not None:
        payload["startupId"] = startup_id
    if season_id is not None:
        payload["seasonId"] = season_id
    return client.post(VOTE_RECORD_LIST_PATH, json=payload)
