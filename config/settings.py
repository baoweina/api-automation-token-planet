"""接口自动化环境配置。

所有可变配置统一从环境变量（或项目根目录下的 .env 文件）读取，
不在代码里硬编码任何账号、密码、Token 等敏感信息。
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    # 测试环境网关地址（Swagger 文档 servers 声明的是内网地址，
    # 实测确认 test.tokenplanet.ai 对外网关会代理到同一套后端）
    BASE_URL: str = os.getenv("BASE_URL", "https://test.tokenplanet.ai/app")

    # 通过手动完成一次 Google 三方登录后，从浏览器抓取的后端会话 Token
    # （Authorization: Bearer <AUTH_TOKEN}），需要定期人工刷新，
    # 详见 README「Token 获取与刷新」章节。
    AUTH_TOKEN: str = os.getenv("AUTH_TOKEN", "")

    # 人工完成一次 Google OAuth 授权后拿到的原始 thirdAuthToken（Google id_token），
    # 专用于直接验证 /exio/user/login 的 THIRD_AUTH(Google) 登录场景本身。
    # 该 token 有效期很短（通常 1 小时内），需要在每次要跑该用例前人工刷新，
    # 未配置或已过期时，对应用例会判定为失败（不是跳过）。
    GOOGLE_THIRD_AUTH_TOKEN: str = os.getenv("GOOGLE_THIRD_AUTH_TOKEN", "")
    # 用于人工获取 thirdAuthToken 时登录的 Google 测试账号，只在 .env 里配置，
    # 不在代码里写死具体账号（这是个人账号信息，不应该出现在仓库里）。
    GOOGLE_LOGIN_USERNAME: str = os.getenv("GOOGLE_LOGIN_USERNAME", "")

    # 接口要求的必传/常用请求头，可按需通过环境变量覆盖
    CONTENT_LANGUAGE: str = os.getenv("CONTENT_LANGUAGE", "zh_CN")
    DEVICE_TYPE: str = os.getenv("DEVICE_TYPE", "PC")
    CLIENT_TYPE: str = os.getenv("CLIENT_TYPE", "PC")
    USER_TYPE: str = os.getenv("USER_TYPE", "APP")

    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "15"))

    # 测试环境数据库（仅用于测试数据准备，比如从 nw_app_mail 表读取邮箱验证码）
    # 只从 .env 读取，不要硬编码到代码里，.env 已在 .gitignore 中排除
    DB_HOST: str = os.getenv("DB_HOST", "")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "nativewallet")

    @classmethod
    def default_headers(cls) -> dict:
        return {
            "Content-Type": "application/json",
            "Content-Language": cls.CONTENT_LANGUAGE,
            "Device-Type": cls.DEVICE_TYPE,
            "Client-Type": cls.CLIENT_TYPE,
            "User-Type": cls.USER_TYPE,
        }


settings = Settings()
