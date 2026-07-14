"""用户登录接口（/exio/user/login、/exio/user/info）用例。

说明：
- 该接口支持 PASSWORD / CAPTCHA / THIRD_AUTH / PASSKEY / NONE 五种登录验证方式。
- 本次业务需求确定使用 THIRD_AUTH(Google) 方式登录。Google OAuth 授权流程
  必须由账号所有者在真实浏览器完成人工验证（密码/Passkey/设备确认），无法通过
  requests/pytest 脚本模拟获取 thirdAuthToken，因此该 token 通过人工获取后写入
  .env（GOOGLE_THIRD_AUTH_TOKEN），用例本身正常执行断言：
  只要 Google 登录没有成功（未配置 token / token 过期 / 校验不通过），
  该用例就判定为 FAILED，不做 skip 处理。
- /exio/user/info（登录后查询用户信息）也归到"用户登录接口"这个 Feature 下，
  因为它测的是登录态相关能力，不是一个独立业务模块。
"""
from __future__ import annotations

import uuid

import allure
import pytest

from api.auth_api import get_user_info, login, send_email_code
from config.settings import settings
from testcases.allure_labels import EPIC, FEATURE_LOGIN
from utils.allure_helpers import verify
from utils.db_client import get_mail_code_by_session_id
from utils.schema_validator import validate_schema


def _random_test_email() -> str:
    """构造一个格式合法、每次运行都不同的测试邮箱（不需要真实存在/能收信）。"""
    return f"qa.automation.{uuid.uuid4().hex[:10]}@example.com"

# 注意：OpenAPI 文档里 ResultLoginInfoDto.data 没有标注 nullable，
# 但业务失败时后端实际返回 data: null，所以失败场景的断言直接校验
# code/msg/data 字段值，不对整个响应体做严格 schema 校验；
# 只有登录成功、data 有实际内容时才用 validate_schema 做结构校验。

VALID_BASE_PAYLOAD = {
    "loginVerifyType": "CAPTCHA",
    "captchaType": "EMAIL",
    "action": "login",
    "username": "qa.automation.negative@example.com",
    "captcha": "000000",
    "sessionId": "00000000-0000-0000-0000-000000000000",
}


@allure.epic(EPIC)
@allure.feature(FEATURE_LOGIN)
@allure.parent_suite(EPIC)
@allure.suite(FEATURE_LOGIN)
class TestLoginNegative:
    @allure.story("参数为空")
    @allure.title("缺少必填字段 username 时应返回 1100 参数校验错误")
    @pytest.mark.negative
    def test_login_missing_username(self, api_client):
        payload = {**VALID_BASE_PAYLOAD}
        payload.pop("username")

        resp = api_client.post("/exio/user/login", json=payload)
        body = resp.json()

        with verify("HTTP 状态码为 200", expected=200, actual=resp.status_code):
            assert resp.status_code == 200
        with verify("业务返回码为 1100", expected=1100, actual=body["code"]):
            assert body["code"] == 1100
        with verify(
            "msg 精确匹配",
            expected="username:params cannot be null",
            actual=body["msg"],
        ):
            assert body["msg"] == "username:params cannot be null"
        with verify("data 为空", expected=None, actual=body["data"]):
            assert body["data"] is None

    @allure.story("参数非法")
    @allure.title("loginVerifyType 传非法枚举值时应返回 1103 参数格式错误")
    @pytest.mark.negative
    def test_login_invalid_verify_type_enum(self, api_client):
        payload = {**VALID_BASE_PAYLOAD, "loginVerifyType": "INVALID_TYPE"}

        resp = api_client.post("/exio/user/login", json=payload)
        body = resp.json()

        with verify("业务返回码为 1103", expected=1103, actual=body["code"]):
            assert body["code"] == 1103
        with verify(
            "msg 精确匹配",
            expected="The request parameter format is not supported",
            actual=body["msg"],
        ):
            assert body["msg"] == "The request parameter format is not supported"
        with verify("data 为空", expected=None, actual=body["data"]):
            assert body["data"] is None

    @allure.story("请求头缺失")
    @allure.title("缺少 Content-Language 请求头时应返回 1104 缺少必传header")
    @pytest.mark.negative
    def test_login_missing_content_language_header(self, api_client):
        # ApiClient 默认会带上 Content-Language，这里用 requests 的约定
        # （header 值传 None 表示本次请求不发送该 header）来复现"缺失"场景
        resp = api_client.post(
            "/exio/user/login",
            json=VALID_BASE_PAYLOAD,
            headers={"Content-Language": None},
        )
        body = resp.json()

        with verify("业务返回码为 1104", expected=1104, actual=body["code"]):
            assert body["code"] == 1104
        with verify(
            "msg 包含 Content-Language 关键字",
            expected_contains="Content-Language",
            actual=body["msg"],
        ):
            assert "Content-Language" in body["msg"]
        with verify("data 为空", expected=None, actual=body["data"]):
            assert body["data"] is None

    @allure.story("验证码/sessionId失效")
    @allure.title("sessionId/验证码不匹配或已失效时应返回 2116 邮箱验证码已过期")
    @pytest.mark.negative
    def test_login_invalid_session_and_captcha(self, api_client):
        payload = {
            **VALID_BASE_PAYLOAD,
            "username": "nonexist_user_automation@example.com",
            "captcha": "000000",
            "sessionId": "00000000-0000-0000-0000-000000000000",
        }

        resp = api_client.post("/exio/user/login", json=payload)
        body = resp.json()

        with verify("业务返回码为 2116", expected=2116, actual=body["code"]):
            assert body["code"] == 2116
        with verify(
            "msg 精确匹配", expected="邮箱验证码已过期", actual=body["msg"]
        ):
            assert body["msg"] == "邮箱验证码已过期"
        with verify("data 为空", expected=None, actual=body["data"]):
            assert body["data"] is None

    @allure.story("第三方Token非法")
    @allure.title("非法 Google thirdAuthToken 应返回 1201 校验失败，而不是登录成功")
    @pytest.mark.negative
    def test_login_invalid_google_third_auth_token(self, api_client):
        payload = {
            "loginVerifyType": "THIRD_AUTH",
            "thirdAuthType": "Google",
            "thirdAuthToken": "fake-token-for-negative-case",
            "thirdId": "",
            "sessionId": "",
            "username": settings.GOOGLE_LOGIN_USERNAME,
            "captcha": "",
            "captchaType": "NONE",
            "action": "login",
        }

        resp = login(api_client, payload)
        body = resp.json()

        with verify("业务返回码为 1201", expected=1201, actual=body["code"]):
            assert body["code"] == 1201
        with verify("data 为空", expected=None, actual=body["data"]):
            assert body["data"] is None


@allure.epic(EPIC)
@allure.feature(FEATURE_LOGIN)
@allure.parent_suite(EPIC)
@allure.suite(FEATURE_LOGIN)
class TestLoginEmailCaptchaSuccess:
    """邮箱动态验证码登录成功场景。

    测试环境下不方便解析真实邮件，验证码直接从测试库 nw_app_mail 表读取
    （该表 id 字段就是发码接口返回的 sessionId，一一对应，详见
    utils/db_client.py）。数据库连接信息只从 .env 读取，不写死在代码里。
    邮箱本身是每次运行随机生成的合法格式地址，不需要真实存在。
    """

    @allure.story("验证码登录成功")
    @allure.title("使用邮箱动态验证码完成登录，应返回登录成功")
    @pytest.mark.smoke
    def test_login_with_email_captcha_success(self, api_client):
        email = _random_test_email()

        with allure.step(f"发送邮箱验证码: {email}"):
            send_resp = send_email_code(api_client, email)
            send_body = send_resp.json()
            assert send_body["code"] == 0, f"发送验证码接口失败: {send_body}"
            session_id = send_body["data"]

        with allure.step("从测试环境数据库 nw_app_mail 表读取动态验证码"):
            code = get_mail_code_by_session_id(session_id)
            allure.attach(
                f"sessionId={session_id}, code_found={code is not None}",
                name="数据库查询结果",
                attachment_type=allure.attachment_type.TEXT,
            )
            assert code, "未能从数据库读取到验证码，请检查发码是否成功/DB 连接是否正常"

        payload = {
            "loginVerifyType": "CAPTCHA",
            "captchaType": "EMAIL",
            "action": "login",
            "username": email,
            "captcha": code,
            "sessionId": session_id,
        }
        resp = login(api_client, payload)
        body = resp.json()

        with verify("业务返回码为 0（登录成功）", expected=0, actual=body["code"]):
            assert body["code"] == 0, f"邮箱验证码登录未成功，接口返回: {body}"

        data = body["data"]
        with verify("data 不为空", expected="not None", actual=data):
            assert data is not None, "登录成功但 data 为空，判定不通过"

        validate_schema(body, "ResultLoginInfoDto")

        with verify("邮箱与登录账号一致", expected=email, actual=data["mail"]):
            assert data["mail"] == email
        with verify(
            "userRoleList 取值范围合法",
            expected="subset of STARTUP/INVESTOR/GUEST",
            actual=data["userRoleList"],
        ):
            assert isinstance(data["userRoleList"], list)
            assert set(data["userRoleList"]) <= {"STARTUP", "INVESTOR", "GUEST"}


@allure.epic(EPIC)
@allure.feature(FEATURE_LOGIN)
@allure.parent_suite(EPIC)
@allure.suite(FEATURE_LOGIN)
class TestLoginThirdAuthGoogle:
    @allure.story("Google登录成功")
    @allure.title("使用 Google 三方登录，登录不成功则本用例判定为不通过")
    def test_login_with_google_third_auth(self, api_client):
        with allure.step("前置条件：GOOGLE_THIRD_AUTH_TOKEN 需人工获取并配置在 .env"):
            assert settings.GOOGLE_THIRD_AUTH_TOKEN, (
                "未配置 GOOGLE_THIRD_AUTH_TOKEN：需要账号所有者在真实浏览器完成一次 "
                "Google 登录，抓取 thirdAuthToken 后写入 .env，否则视为登录未成功，"
                "本用例判定为不通过（详见 README「Token 获取与刷新」）"
            )

        payload = {
            "loginVerifyType": "THIRD_AUTH",
            "thirdAuthType": "Google",
            "thirdAuthToken": settings.GOOGLE_THIRD_AUTH_TOKEN,
            "thirdId": "",
            "sessionId": "",
            "username": settings.GOOGLE_LOGIN_USERNAME,
            "captcha": "",
            "captchaType": "NONE",
            "action": "login",
        }

        resp = login(api_client, payload)
        body = resp.json()

        with verify("业务返回码为 0（登录成功）", expected=0, actual=body["code"]):
            assert body["code"] == 0, f"Google 登录未成功，接口返回: {body}"

        data = body["data"]
        with verify("data 不为空", expected="not None", actual=data):
            assert data is not None, "登录成功但 data 为空，判定不通过"

        validate_schema(body, "ResultLoginInfoDto")

        with verify(
            "邮箱与登录账号一致",
            expected=settings.GOOGLE_LOGIN_USERNAME,
            actual=data["mail"],
        ):
            assert data["mail"] == settings.GOOGLE_LOGIN_USERNAME
        with verify("loginId 为正整数", expected=">0", actual=data["loginId"]):
            # loginId 后端可能序列化成字符串（int64 精度保护），这里统一转 int 判断
            assert int(data["loginId"]) > 0
        with verify(
            "userRoleList 取值范围合法",
            expected="subset of STARTUP/INVESTOR/GUEST",
            actual=data["userRoleList"],
        ):
            assert isinstance(data["userRoleList"], list)
            assert set(data["userRoleList"]) <= {"STARTUP", "INVESTOR", "GUEST"}


@allure.epic(EPIC)
@allure.feature(FEATURE_LOGIN)
@allure.parent_suite(EPIC)
@allure.suite(FEATURE_LOGIN)
class TestUserInfo:
    """登录态查询用户信息（/exio/user/info），归属"用户登录接口"这个业务模块。"""

    @allure.story("登录后查询用户信息成功")
    @allure.title("携带有效 Bearer Token 获取用户角色信息，响应结构应符合 OpenAPI 定义")
    @pytest.mark.needs_auth
    def test_get_user_info_success(self, authed_client):
        resp = get_user_info(authed_client)
        body = resp.json()
        validate_schema(body, "ResultUserRoleInfoDto")

        with verify("业务返回码为 0", expected=0, actual=body["code"]):
            assert body["code"] == 0, f"预期登录态有效、接口返回成功，实际返回: {body}"

        data = body["data"]
        with verify("data 不为空", expected="not None", actual=data):
            assert data is not None, "登录态有效时 data 不应为空"

        role_list = data.get("userRoleList") or []
        with verify(
            "userRoleList 取值范围合法",
            expected="subset of STARTUP/INVESTOR/GUEST",
            actual=role_list,
        ):
            assert isinstance(role_list, list)
            assert set(role_list) <= {"STARTUP", "INVESTOR", "GUEST"}

    @allure.story("未登录访问用户信息")
    @allure.title("未携带 Authorization 时访问需登录接口应被拒绝")
    @pytest.mark.negative
    def test_get_user_info_without_token_should_fail(self, api_client):
        resp = get_user_info(api_client)
        body = resp.json()

        with verify("业务返回码不为 0", expected="!=0", actual=body["code"]):
            assert body["code"] != 0, "未登录状态下不应能正常获取用户信息"
        with verify("data 为空", expected=None, actual=body["data"]):
            assert body["data"] is None

    @allure.story("Token非法访问用户信息")
    @allure.title("携带无效/伪造 Token 访问需登录接口应被拒绝")
    @pytest.mark.negative
    def test_get_user_info_with_invalid_token_should_fail(self, api_client):
        api_client.set_token("this-is-not-a-valid-jwt-token")

        resp = get_user_info(api_client)
        body = resp.json()

        with verify("业务返回码不为 0", expected="!=0", actual=body["code"]):
            assert body["code"] != 0, "非法 Token 不应被接受"
        with verify("data 为空", expected=None, actual=body["data"]):
            assert body["data"] is None
