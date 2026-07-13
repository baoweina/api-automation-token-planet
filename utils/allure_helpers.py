"""Allure 报告增强工具。

- verify(): 把一组断言包装成带名字的 Allure step，并把期望/实际值作为附件记录。
- attach_failure_snapshot(): 用例失败时，把最近一次请求/响应渲染成图片+JSON附加到报告。
"""
from __future__ import annotations

import contextlib
import json
import textwrap
from typing import Any, Iterator

import allure
from PIL import Image, ImageDraw, ImageFont

from api.client import LastExchange, get_last_exchange


@contextlib.contextmanager
def verify(title: str, **expected_vs_actual: Any) -> Iterator[None]:
    """包装断言并记录断言结果。"""
    with allure.step(f"断言：{title}"):
        allure.attach(
            json.dumps(expected_vs_actual, ensure_ascii=False, indent=2, default=str),
            name="断言结果",
            attachment_type=allure.attachment_type.JSON,
        )
        yield


def _render_text_image(lines: list[str], *, width: int = 1000) -> bytes:
    font = ImageFont.load_default()
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(textwrap.wrap(line, width=110) or [""])

    line_height = 16
    padding = 20
    height = padding * 2 + line_height * len(wrapped)
    image = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(image)
    for i, line in enumerate(wrapped):
        draw.text((padding, padding + i * line_height), line, fill="black", font=font)

    from io import BytesIO

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def attach_failure_snapshot(test_name: str) -> None:
    """用例失败时调用：把最近一次请求/响应渲染成截图附件到 Allure。"""
    exchange: LastExchange | None = get_last_exchange()
    if exchange is None:
        return

    lines = [
        f"用例: {test_name}",
        f"请求: {exchange.method} {exchange.url}",
        f"请求参数: {json.dumps(exchange.request_payload, ensure_ascii=False, default=str)}",
        f"响应状态码: {exchange.status_code}",
        f"响应内容: {json.dumps(exchange.response_body, ensure_ascii=False, default=str)}",
    ]

    allure.attach(
        _render_text_image(lines),
        name="失败截图（最近一次接口请求/响应）",
        attachment_type=allure.attachment_type.PNG,
    )
    allure.attach(
        json.dumps(
            {
                "request": {
                    "method": exchange.method,
                    "url": exchange.url,
                    "payload": exchange.request_payload,
                },
                "response": {
                    "status_code": exchange.status_code,
                    "body": exchange.response_body,
                },
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        name="失败快照（JSON）",
        attachment_type=allure.attachment_type.JSON,
    )
