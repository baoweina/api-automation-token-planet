"""测试环境数据库直连工具（仅用于测试数据准备/断言，不是业务代码）。

数据库连接信息只从 .env 读取（DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME），
不要硬编码到代码里，.env 已在 .gitignore 中排除，不会提交到 git。
"""
from __future__ import annotations

import time

import pymysql
import pymysql.cursors

from config.settings import settings


def _connect() -> pymysql.connections.Connection:
    if not settings.DB_HOST:
        raise RuntimeError(
            "未配置数据库连接信息（DB_HOST 等），无法读取邮箱验证码，请检查 .env"
        )
    return pymysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
        connect_timeout=10,
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_mail_code_by_session_id(
    session_id: str, *, retries: int = 5, interval_sec: float = 1.0
) -> str | None:
    """按 sessionId（对应 nw_app_mail.id）查询邮箱验证码，带重试避免落库时序延迟。"""
    for attempt in range(retries):
        conn = _connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT code FROM nw_app_mail WHERE id = %s", (session_id,)
                )
                row = cur.fetchone()
        finally:
            conn.close()

        if row and row.get("code"):
            return row["code"]
        time.sleep(interval_sec)

    return None
