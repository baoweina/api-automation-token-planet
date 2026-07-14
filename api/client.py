"""统一的 HTTP 客户端封装。

- 统一注入默认请求头、Base URL、超时时间
- 每次请求自动把 请求/响应 以 Allure attachment 形式记录，报告里能直接看到接口细节
- 记录"最近一次请求/响应"到模块级缓存，供 conftest.py 在用例失败时生成失败快照使用
- 对外只暴露 get/post/put/delete 四个方法，业务接口封装（api/*.py）在此基础上组装
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import allure
import requests

from config.settings import settings


@dataclass
class LastExchange:
    """最近一次请求/响应的快照，用于失败时生成截图附件。"""

    method: str
    url: str
    request_payload: dict
    status_code: int
    response_body: Any


_last_exchange: LastExchange | None = None


def get_last_exchange() -> LastExchange | None:
    """获取当前进程内最近一次接口调用的请求/响应，测试失败时用来生成截图。"""
    return _last_exchange


class ApiClient:
    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = (base_url or settings.BASE_URL).rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(settings.default_headers())
        if token:
            self.set_token(token)

    def set_token(self, token: str) -> None:
        self.session.headers["Authorization"] = f"Bearer {token}"

    def _full_url(self, path: str) -> str:
        return f"{self.base_url}{path if path.startswith('/') else '/' + path}"

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = self._full_url(path)
        kwargs.setdefault("timeout", settings.REQUEST_TIMEOUT)

        with allure.step(f"{method.upper()} {path}"):
            request_payload = self._attach_request(method, url, kwargs)
            response = self.session.request(method, url, **kwargs)
            response_body = self._attach_response(response)
            self._remember_exchange(method, url, request_payload, response, response_body)
            return response

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("DELETE", path, **kwargs)

    @staticmethod
    def _attach_request(method: str, url: str, kwargs: dict) -> dict:
        payload = {
            "method": method.upper(),
            "url": url,
            "params": kwargs.get("params"),
            "json": kwargs.get("json"),
            "extra_headers": kwargs.get("headers"),
        }
        allure.attach(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            name="Request",
            attachment_type=allure.attachment_type.JSON,
        )
        return payload

    @staticmethod
    def _attach_response(response: requests.Response) -> Any:
        try:
            body: Any = response.json()
        except ValueError:
            body = response.text
        payload = {
            "status_code": response.status_code,
            "elapsed_ms": round(response.elapsed.total_seconds() * 1000, 1),
            "body": body,
        }
        allure.attach(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            name="Response",
            attachment_type=allure.attachment_type.JSON,
        )
        return body

    @staticmethod
    def _remember_exchange(
        method: str,
        url: str,
        request_payload: dict,
        response: requests.Response,
        response_body: Any,
    ) -> None:
        global _last_exchange
        _last_exchange = LastExchange(
            method=method.upper(),
            url=url,
            request_payload=request_payload,
            status_code=response.status_code,
            response_body=response_body,
        )
