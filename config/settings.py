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
    BASE_URL: str = os.getenv("BASE_URL", "https://test.tokenplanet.ai/app")

    AUTH_TOKEN: str = os.getenv("AUTH_TOKEN", "")

    GOOGLE_THIRD_AUTH_TOKEN: str = os.getenv("GOOGLE_THIRD_AUTH_TOKEN", "")
    # 用于人工获取 thirdAuthToken 时登录的 Google 测试账号，只在 .env 里配置，
    # 不在代码里写死具体账号
    GOOGLE_LOGIN_USERNAME: str = os.getenv("GOOGLE_LOGIN_USERNAME", "")

    CONTENT_LANGUAGE: str = os.getenv("CONTENT_LANGUAGE", "zh_CN")
    DEVICE_TYPE: str = os.getenv("DEVICE_TYPE", "PC")
    CLIENT_TYPE: str = os.getenv("CLIENT_TYPE", "PC")
    USER_TYPE: str = os.getenv("USER_TYPE", "APP")

    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "15"))

    # 测试环境数据库（仅用于测试数据准备，只从 .env 读取，不硬编码）
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
