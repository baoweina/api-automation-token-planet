from __future__ import annotations

import pytest

from api.client import ApiClient
from config.settings import settings
from utils.allure_helpers import attach_failure_snapshot


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """用例失败（assert 失败或抛异常）时，把最近一次接口请求/响应渲染成截图附件。

    只在 call 阶段（用例函数本身执行阶段，不是 setup/teardown）失败时触发，
    避免 fixture 报错（比如没配置 AUTH_TOKEN 导致的 skip）也被当成失败截图。
    """
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        attach_failure_snapshot(item.nodeid)


@pytest.fixture
def api_client() -> ApiClient:
    """未携带登录态的裸客户端，用于登录接口本身的正向/反向测试。

    注意：必须是 function 级别（每个用例一个新实例），而不能是 session 级别。
    因为部分反向用例会调用 api_client.set_token(...) 往同一个 requests.Session
    上设置 Authorization header，如果多个用例共用同一个客户端实例，
    前一个用例设置的 Token 会"泄漏"污染到后面的用例，导致断言基于错误的鉴权状态。
    """
    return ApiClient()


@pytest.fixture
def authed_client() -> ApiClient:
    """携带登录态（Bearer Token）的客户端。

    Token 来自人工完成一次 Google 三方登录后从浏览器抓取、写入 .env 的
    AUTH_TOKEN。若未配置则跳过依赖登录态的用例，详见 README。
    """
    if not settings.AUTH_TOKEN:
        pytest.skip(
            "未配置 AUTH_TOKEN：请先在真实浏览器完成一次 Google 登录，"
            "抓取后端签发的 Bearer Token 并写入 .env（参考 README「Token 获取与刷新」）"
        )
    return ApiClient(token=settings.AUTH_TOKEN)
