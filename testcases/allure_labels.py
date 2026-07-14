"""Allure Epic / Feature 常量，统一维护，避免各测试文件里的字符串拼错、对不齐。

层级约定：
    Epic    （全局唯一）  接口自动化测试
    Feature （按接口/业务模块）  用户登录接口 / 首页接口
    Story   （按测试场景，在各测试文件里用 @allure.story 标在具体用例上）
"""

EPIC = "接口自动化测试"

FEATURE_LOGIN = "用户登录接口"
FEATURE_HOME = "首页接口"
FEATURE_VOTE_RECORD = "项目认筹记录接口"
