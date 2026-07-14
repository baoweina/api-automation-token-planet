"""登录注册模块相关接口封装。

对应 OpenAPI 文档 tag: "Exio home管理API_(WEB)"
参考: openapi/wali_openapi.json -> paths./exio/user/login
"""
from __future__ import annotations

import requests

from api.client import ApiClient

LOGIN_PATH = "/exio/user/login"
SEND_EMAIL_CODE_PATH = "/manage/v1/common/security/exio/no_authentication/mail"
USER_INFO_PATH = "/exio/user/info"


def login(client: ApiClient, payload: dict) -> requests.Response:
    """登录/注册接口。

    payload 字段说明（详见 OpenAPI: APP用户登录请求信息）:
        loginVerifyType: PASSWORD | CAPTCHA | THIRD_AUTH | PASSKEY | NONE
        thirdAuthType:   Google | AppleID | Facebook（仅 THIRD_AUTH 需要）
        thirdAuthToken:  第三方授权 token（仅 THIRD_AUTH 需要，需真实 Google 登录换取）
        username:        email / phone
        captcha/captchaType/sessionId: 验证码登录相关
        action:           login 等
    """
    return client.post(LOGIN_PATH, json=payload)


def send_email_code(client: ApiClient, mail: str) -> requests.Response:
    """发送邮箱验证码，返回值 data 字段为登录时需要携带的 sessionId。"""
    return client.post(SEND_EMAIL_CODE_PATH, params={"mail": mail})


def get_user_info(client: ApiClient) -> requests.Response:
    """获取当前登录用户角色信息，需要携带有效 Authorization Bearer Token。"""
    return client.get(USER_INFO_PATH)
