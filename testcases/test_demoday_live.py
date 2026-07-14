"""首页接口：获取 Demoday 正在讲解的项目（/exio/demoday/live）用例。

已实测确认：该接口是真正强制校验登录态的接口（不同于 login/发验证码接口），
未携带 Authorization 时，无论请求体是否合法，都会先返回 2113 unauthorized access，
即鉴权检查在参数校验之前；但如果显式传了违反 pageSize 边界的值，会先被参数校验拦住
（返回 2110，文案复用了"登录信息已过期"，实际含义是参数非法，不要被文案误导）。

- 不依赖登录态、可无人值守稳定运行的场景：未登录访问、非法 Token
- 分页参数边界值、成功场景等，都需要 authed_client（AUTH_TOKEN 未配置时自动 skip）
"""
from __future__ import annotations

import allure
import pytest

from api.demoday_api import get_demoday_live
from testcases.allure_labels import EPIC, FEATURE_HOME
from utils.allure_helpers import verify
from utils.schema_validator import validate_schema

UNAUTHORIZED_CODE = 2113


@allure.epic(EPIC)
@allure.feature(FEATURE_HOME)
@allure.parent_suite(EPIC)
@allure.suite(FEATURE_HOME)
class TestDemodayLiveNegative:
    @allure.story("未登录访问")
    @allure.title("未携带 Authorization 时应返回 2113 unauthorized access")
    @pytest.mark.negative
    def test_get_demoday_live_without_token_should_fail(self, api_client):
        resp = get_demoday_live(api_client, page_no=1, page_size=10)
        body = resp.json()

        with verify("业务返回码为 2113", expected=UNAUTHORIZED_CODE, actual=body["code"]):
            assert body["code"] == UNAUTHORIZED_CODE
        with verify(
            "msg 精确匹配", expected="unauthorized access", actual=body["msg"]
        ):
            assert body["msg"] == "unauthorized access"
        with verify("data 为空", expected=None, actual=body["data"]):
            assert body["data"] is None

    @allure.story("Token失效")
    @allure.title("携带无效/伪造 Token 时不应返回登录用户才能看到的数据")
    @pytest.mark.negative
    def test_get_demoday_live_with_invalid_token_should_fail(self, api_client):
        api_client.set_token("this-is-not-a-valid-jwt-token")

        resp = get_demoday_live(api_client, page_no=1, page_size=10)
        body = resp.json()

        with verify("业务返回码不为 0", expected="!=0", actual=body["code"]):
            assert body["code"] != 0, "非法 Token 不应被当作已登录处理"
        with verify("data 为空", expected=None, actual=body["data"]):
            assert body["data"] is None

    @allure.story("参数非法")
    @allure.title("即使参数非法，未登录时也应先被鉴权拦截（返回 2113 而不是参数校验错误）")
    @pytest.mark.negative
    def test_get_demoday_live_auth_check_before_param_validation(self, api_client):
        # pageSize 传 0（违反 schema minimum=1），但由于鉴权检查优先，
        # 实测确认依然是 2113，而不是参数校验类错误码
        resp = get_demoday_live(api_client, page_no=1, page_size=0)
        body = resp.json()

        with verify("业务返回码为 2113", expected=UNAUTHORIZED_CODE, actual=body["code"]):
            assert body["code"] == UNAUTHORIZED_CODE


@allure.epic(EPIC)
@allure.feature(FEATURE_HOME)
@allure.parent_suite(EPIC)
@allure.suite(FEATURE_HOME)
@pytest.mark.needs_auth
class TestDemodayLiveSuccess:
    @allure.story("查询成功")
    @allure.title("携带有效 Bearer Token 获取正在讲解的项目，响应结构应符合 OpenAPI 定义")
    def test_get_demoday_live_success(self, authed_client):
        resp = get_demoday_live(authed_client, page_no=1, page_size=10)
        body = resp.json()
        validate_schema(body, "ResultExio初创企业项目详情-web")

        with verify("业务返回码为 0", expected=0, actual=body["code"]):
            assert body["code"] == 0, f"预期获取成功，实际返回: {body}"

        data = body["data"]
        # data 为空代表"当前没有正在讲解的项目"，属于合法业务状态；
        # 有数据时校验关键字段类型是否符合预期
        if data is not None:
            with allure.step("有数据时校验关键字段类型"):
                if data.get("id") is not None:
                    # id 是 int64，后端可能序列化成字符串（精度保护，实测在
                    # loginId 上确认过这个模式），这里同时容忍 int/字符串数字
                    assert isinstance(data["id"], (int, str))
                    assert int(data["id"]) > 0
                if data.get("isRoadshowLive") is not None:
                    assert isinstance(data["isRoadshowLive"], bool)
                if data.get("investorsCount") is not None:
                    assert isinstance(data["investorsCount"], int)

    @allure.story("参数超限")
    @allure.title("pageSize 传超出上限(101)应被参数校验拦截，不返回成功")
    def test_get_demoday_live_page_size_exceeds_max(self, authed_client):
        # OpenAPI: pageSize maximum=100，这里故意传 101 验证边界校验生效
        resp = get_demoday_live(authed_client, page_no=1, page_size=101)
        body = resp.json()

        with verify("业务返回码不为 0", expected="!=0", actual=body["code"]):
            assert body["code"] != 0, "pageSize 超出上限时不应返回成功"

    @allure.story("数据为空")
    @allure.title("按 projectName 模糊搜索一个几乎不可能存在的名称，应正常返回空结果而非报错")
    def test_get_demoday_live_search_by_unlikely_project_name(self, authed_client):
        resp = get_demoday_live(
            authed_client,
            page_no=1,
            page_size=10,
            project_name="__automation_unlikely_project_name__",
        )
        body = resp.json()

        with verify("业务返回码为 0", expected=0, actual=body["code"]):
            assert body["code"] == 0
