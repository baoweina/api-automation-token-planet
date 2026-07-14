"""项目认筹记录接口：获取投资方认筹记录分页（/exio/startup/vote-record/list）用例。

已实测确认，该接口的校验顺序与 /exio/demoday/live 不同：
- 必填参数缺失/越界（缺 startupId、pageSize 超出 [1,100]）优先于鉴权检查，
  未登录时依然会先返回 1100 参数校验错误，而不是 2113。
- 只有参数合法时，未登录才会返回 2113 unauthorized access。
- 携带无效/伪造 Token 时返回 2110（"Your login information has expired.
  Please log in again"），跟 /exio/demoday/live 对无效 Token 的表现不一样，
  这里按接口分别实测确认过的真实返回码断言，不跨接口假设一致的错误码。

- 不依赖登录态、可无人值守稳定运行的场景：参数缺失/越界、未登录访问、非法 Token
- 分页参数边界值、成功场景等，都需要 authed_client（AUTH_TOKEN 未配置时自动 skip）
"""
from __future__ import annotations

import allure
import pytest

from api.startup_api import get_investor_vote_record_page
from testcases.allure_labels import EPIC, FEATURE_VOTE_RECORD
from utils.allure_helpers import verify
from utils.schema_validator import validate_schema

PARAM_ERROR_CODE = 1100
UNAUTHORIZED_CODE = 2113
TOKEN_EXPIRED_CODE = 2110


@allure.epic(EPIC)
@allure.feature(FEATURE_VOTE_RECORD)
@allure.parent_suite(EPIC)
@allure.suite(FEATURE_VOTE_RECORD)
class TestVoteRecordNegative:
    @allure.story("参数为空")
    @allure.title("缺少必填字段 startupId 时应返回 1100 参数校验错误")
    @pytest.mark.negative
    def test_missing_startup_id_should_fail(self, api_client):
        resp = get_investor_vote_record_page(
            api_client, page_no=1, page_size=10, startup_id=None
        )
        body = resp.json()

        with verify("业务返回码为 1100", expected=PARAM_ERROR_CODE, actual=body["code"]):
            assert body["code"] == PARAM_ERROR_CODE
        with verify("msg 提示 startupId 不能为空", expected="startupId", actual=body["msg"]):
            assert "startupId" in body["msg"]
        with verify("data 为空", expected=None, actual=body["data"]):
            assert body["data"] is None

    @allure.story("参数非法")
    @allure.title("pageSize 传 0（小于最小值 1）应返回 1100 参数校验错误")
    @pytest.mark.negative
    def test_page_size_below_min_should_fail(self, api_client):
        resp = get_investor_vote_record_page(
            api_client, page_no=1, page_size=0, startup_id=1
        )
        body = resp.json()

        with verify("业务返回码为 1100", expected=PARAM_ERROR_CODE, actual=body["code"]):
            assert body["code"] == PARAM_ERROR_CODE
        with verify(
            "msg 提示 pageSize 越界", expected="pageSize", actual=body["msg"]
        ):
            assert "pageSize" in body["msg"]

    @allure.story("参数非法")
    @allure.title("pageSize 传 101（大于最大值 100）应返回 1100 参数校验错误")
    @pytest.mark.negative
    def test_page_size_exceeds_max_should_fail(self, api_client):
        resp = get_investor_vote_record_page(
            api_client, page_no=1, page_size=101, startup_id=1
        )
        body = resp.json()

        with verify("业务返回码为 1100", expected=PARAM_ERROR_CODE, actual=body["code"]):
            assert body["code"] == PARAM_ERROR_CODE
        with verify(
            "msg 提示 pageSize 越界", expected="pageSize", actual=body["msg"]
        ):
            assert "pageSize" in body["msg"]

    @allure.story("未登录访问")
    @allure.title("参数合法但未携带 Authorization 时应返回 2113 unauthorized access")
    @pytest.mark.negative
    def test_without_token_should_fail(self, api_client):
        resp = get_investor_vote_record_page(
            api_client, page_no=1, page_size=10, startup_id=1, season_id=0
        )
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
    @allure.title("携带无效/伪造 Token 时应返回 2110 登录信息已过期")
    @pytest.mark.negative
    def test_with_invalid_token_should_fail(self, api_client):
        api_client.set_token("this-is-not-a-valid-jwt-token")

        resp = get_investor_vote_record_page(
            api_client, page_no=1, page_size=10, startup_id=1
        )
        body = resp.json()

        with verify("业务返回码为 2110", expected=TOKEN_EXPIRED_CODE, actual=body["code"]):
            assert body["code"] == TOKEN_EXPIRED_CODE
        with verify("data 为空", expected=None, actual=body["data"]):
            assert body["data"] is None


@allure.epic(EPIC)
@allure.feature(FEATURE_VOTE_RECORD)
@allure.parent_suite(EPIC)
@allure.suite(FEATURE_VOTE_RECORD)
@pytest.mark.needs_auth
class TestVoteRecordSuccess:
    @allure.story("查询成功")
    @allure.title("携带有效 Bearer Token 查询认筹记录，响应结构应符合 OpenAPI 定义")
    def test_get_vote_record_success(self, authed_client):
        resp = get_investor_vote_record_page(
            authed_client, page_no=1, page_size=10, startup_id=1
        )
        body = resp.json()
        validate_schema(body, "ResultPageInfoInvestorVoteRecord")

        with verify("业务返回码为 0", expected=0, actual=body["code"]):
            assert body["code"] == 0, f"预期查询成功，实际返回: {body}"

        data = body["data"]
        with allure.step("分页结构字段类型校验"):
            assert isinstance(data["pageNum"], int)
            assert isinstance(data["pageSize"], int)
            assert isinstance(data["list"], list)

    @allure.story("参数边界")
    @allure.title("pageSize 传边界最大值 100 应正常返回成功")
    def test_get_vote_record_page_size_boundary_max(self, authed_client):
        resp = get_investor_vote_record_page(
            authed_client, page_no=1, page_size=100, startup_id=1
        )
        body = resp.json()

        with verify("业务返回码为 0", expected=0, actual=body["code"]):
            assert body["code"] == 0

    @allure.story("赛季筛选")
    @allure.title("seasonId 传 0 代表查询所有赛季，应正常返回成功")
    def test_get_vote_record_season_id_zero_means_all_seasons(self, authed_client):
        resp = get_investor_vote_record_page(
            authed_client, page_no=1, page_size=10, startup_id=1, season_id=0
        )
        body = resp.json()

        with verify("业务返回码为 0", expected=0, actual=body["code"]):
            assert body["code"] == 0

    @allure.story("数据为空")
    @allure.title("查询一个几乎不可能存在的 startupId，应正常返回空列表而非报错")
    def test_get_vote_record_with_unlikely_startup_id(self, authed_client):
        resp = get_investor_vote_record_page(
            authed_client, page_no=1, page_size=10, startup_id=999999999999
        )
        body = resp.json()

        with verify("业务返回码为 0", expected=0, actual=body["code"]):
            assert body["code"] == 0
        with verify("列表为空", expected=0, actual=len(body["data"]["list"])):
            assert body["data"]["list"] == []
