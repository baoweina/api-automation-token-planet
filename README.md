# bwn test demo · 接口自动化

技术栈：Cursor + OpenAPI/Swagger + Pytest + Requests + Allure

被测系统：Token Planet（登录注册模块），测试环境 `https://test.tokenplanet.ai`

## 项目结构

```
config/
  settings.py           环境配置（BASE_URL、Token、数据库连接等，全部从 .env 读取）
api/
  client.py              统一请求封装：注入默认header、Request/Response写入Allure、
                          记录“最近一次请求响应”供失败截图使用
  auth_api.py             登录 / 用户信息接口封装
  demoday_api.py           Demoday 首页接口封装
testcases/
  allure_labels.py        Epic/Feature 常量（Epic：接口自动化测试；
                          Feature：用户登录接口 / 首页接口）
  conftest.py              fixture（api_client/authed_client） +
                          用例失败自动截图的 pytest hook
  test_login.py            Feature: 用户登录接口（登录 + 登录态查用户信息）
  test_demoday_live.py     Feature: 首页接口（Demoday 正在讲解的项目）
utils/
  schema_validator.py      基于 OpenAPI 文档做响应结构 JSON Schema 校验
  allure_helpers.py        verify()断言步骤封装 + 失败截图/快照生成
  db_client.py             测试库直连工具（读取邮箱动态验证码，仅测试数据准备用）
openapi/                  OpenAPI 文档缓存 + 拉取脚本（fetch_openapi.py）
reports/                  Allure 结果与报告输出目录（不提交 git）
run_tests.sh              一键：跑用例 + 生成报告 + 打开报告
```

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env               # 按需填写，见下文「配置说明」
python openapi/fetch_openapi.py    # 拉取一份 OpenAPI 文档缓存（未提交到仓库，见下文说明）

./run_tests.sh          # 跑全部用例 + 生成 Allure 报告 + 自动打开
```

也可以自己分步执行：

```bash
pytest                                                    # 结果写入 reports/allure-results
allure generate reports/allure-results -o reports/allure-report --clean
allure open reports/allure-report                         # 本地打开可视化报告
# 或者一步生成并打开：allure serve reports/allure-results
```

## 配置说明（.env）

所有可变配置都从项目根目录的 `.env` 读取（`.env.example` 是模板，复制改名即可）。
**`.env` 已在 `.gitignore` 中排除，不会被提交到 git，也不要把真实账号密码写进代码或提交的文件里。**

| 变量 | 说明 | 必填 |
| --- | --- | --- |
| `BASE_URL` | 测试环境网关地址 | 已有默认值 |
| `AUTH_TOKEN` | 登录态 Bearer Token（人工获取，见下文） | 依赖登录态的用例需要，未配置自动 `skip` |
| `GOOGLE_THIRD_AUTH_TOKEN` | Google OAuth 原始 `thirdAuthToken`（人工获取） | 仅 Google 登录用例需要，未配置用例判定为 `FAILED` |
| `GOOGLE_LOGIN_USERNAME` | 你自己的 Google 测试账号邮箱 | 同上 |
| `DB_HOST`/`DB_PORT`/`DB_USER`/`DB_PASSWORD`/`DB_NAME` | 测试环境数据库连接信息 | 邮箱验证码登录用例需要 |
| `CONTENT_LANGUAGE`/`DEVICE_TYPE`/`CLIENT_TYPE`/`USER_TYPE`/`REQUEST_TIMEOUT` | 默认请求头/超时，一般不用改 | 否 |

### Token 获取与刷新（重要）

登录接口 `POST /exio/user/login` 支持 `PASSWORD / CAPTCHA / THIRD_AUTH / PASSKEY` 等方式，
当前业务确定使用 **Google 第三方登录（THIRD_AUTH）**。Google OAuth 授权必须由账号所有者在
真实浏览器完成一次人工验证（密码/Passkey/设备确认），**无法通过脚本模拟**，因此本项目采用
「人工登录一次、复用后端 Token」的方案：

1. 用浏览器打开 `https://test.tokenplanet.ai`，点击「登录」→「Continue with Google」，
   用你自己的 Google 测试账号完成一次真实登录
2. 登录成功后，打开浏览器开发者工具 Network 面板，找任意一个登录后发出的接口请求
   （例如 `GET /exio/user/info`），复制其请求头 `Authorization: Bearer <token>` 中
   `<token>` 部分
3. 写入项目根目录 `.env` 文件：
   ```
   AUTH_TOKEN=<刚才复制的token>
   GOOGLE_LOGIN_USERNAME=<你的Google测试账号邮箱>
   ```
4. Token 是 JWT，有过期时间，过期后需要重复上述步骤重新获取

未配置 `AUTH_TOKEN` 时，依赖登录态的用例会自动跳过，不影响其他不需要登录态的用例运行。
`GOOGLE_THIRD_AUTH_TOKEN` 有效期通常在 1 小时内，专用于直接验证 Google 登录场景本身，
需要在每次要跑该用例前人工刷新，未配置或已过期时用例判定为 **FAILED**（不是 skip）。

### 邮箱验证码登录用例：数据库读取验证码

`TestLoginEmailCaptchaSuccess` 用的是**测试环境**数据库直连方案，不需要人工介入、可重复运行：

1. 用例每次随机生成一个格式合法的邮箱（如 `qa.automation.xxxx@example.com`），不需要真实存在
2. 调用发码接口 `POST /manage/v1/common/security/exio/no_authentication/mail?mail=<邮箱>`，
   拿到返回的 `sessionId`
3. 该 `sessionId` 正好就是测试库 `nw_app_mail` 表的主键 `id`，用它去查
   对应的 `code` 字段，即为本次验证码（`utils/db_client.py`）
4. 用邮箱 + 验证码 + sessionId 调用登录接口，断言登录成功

数据库账号密码只从 `.env` 读取，不写死在代码里；连接失败/未配置时用例会直接报错提示检查 `.env`。

## 用例范围说明

- `testcases/test_login.py` — Feature: **用户登录接口**
  - `TestLoginNegative`：缺少必填字段、非法枚举值、缺少必传 header、验证码/session 失效、
    非法 Google thirdAuthToken 等反向场景，均为实测确认过真实返回码的稳定断言，
    不依赖登录态，可随时无人值守运行
  - `TestLoginEmailCaptchaSuccess::test_login_with_email_captcha_success`：
    邮箱动态验证码登录成功场景，全自动、可无人值守重复运行，详见上文
    「邮箱验证码登录用例：数据库读取验证码」
  - `TestLoginThirdAuthGoogle::test_login_with_google_third_auth`：
    **不做 skip**，只要 `GOOGLE_THIRD_AUTH_TOKEN` 未配置、已过期或校验不通过，
    该用例就判定为 **FAILED**（登录不成功 = 用例不通过）
  - `TestUserInfo`：登录态查用户信息（`/exio/user/info`），依赖 `AUTH_TOKEN`
    （seed token）的成功场景未配置时 `skip`；未登录/非法 Token 的反向场景不需要
- `testcases/test_demoday_live.py` — Feature: **首页接口**（`POST /exio/demoday/live`）
  - 反向场景（不依赖登录态，可无人值守运行）：未登录访问返回 `2113 unauthorized access`、
    非法 Token 被拒绝
  - 正向场景（`needs_auth`，依赖 `AUTH_TOKEN`）：成功获取并做响应结构校验、
    `pageSize` 超出上限(100)被拦截、按项目名搜索无结果时仍正常返回

## Allure 报告分级结构

```
Epic     接口自动化测试
├─ Feature  用户登录接口
│   ├─ Story  参数为空 / 参数非法 / 请求头缺失 / 验证码-sessionId失效 /
│   │         第三方Token非法 / 验证码登录成功 / Google登录成功
│   └─ Story  登录后查询用户信息成功 / 未登录访问用户信息 / Token非法访问用户信息
└─ Feature  首页接口
    └─ Story  查询成功 / 未登录访问 / Token失效 / 参数非法 / 参数超限 / 数据为空
```

对应到代码里就是三个装饰器：`@allure.epic(...)` 标在类上（全局一份），
`@allure.feature(...)` 标在类上（每个接口一份），`@allure.story(...)` 标在
每个用例方法上（每个场景一份）：

```python
@allure.epic(EPIC)                 # 接口自动化测试
@allure.feature(FEATURE_LOGIN)     # 用户登录接口
class TestLoginNegative:

    @allure.story("参数为空")       # 具体测试场景
    @allure.title("缺少必填字段 username 时应返回 1100 参数校验错误")
    def test_login_missing_username(self, api_client):
        ...
```

打开报告后点「Behaviors」标签页就是这个 Epic/Feature/Story 三层树。

## 断言与失败截图（Allure 报告增强）

`utils/allure_helpers.py` 提供两个能力：

1. **`verify(title, **expected_vs_actual)`**：把断言包装成带名字的 Allure step，
   并把“期望值 vs 实际值”记录为附件，报告里一眼就能看到断言依据，不用去猜：

   ```python
   with verify("业务返回码为 1100", expected=1100, actual=body["code"]):
       assert body["code"] == 1100
   ```

2. **失败自动截图**：`testcases/conftest.py` 里的 `pytest_runtest_makereport` hook
   会在用例判定为 FAILED 时，自动把“最近一次接口请求/响应”渲染成一张图片
   （因为是接口自动化、没有浏览器页面，这里的“截图”是请求参数+响应内容的可视化快照）
   附加到 Allure 报告，同时附一份 JSON 版本，两者都在失败用例详情页可以直接看到。

每条用例在报告里能看到的信息：请求 URL / 请求参数（`Request` 附件）、
响应结果（`Response` 附件）、每一步的断言依据（`断言：xxx` step + `断言结果` 附件），
失败时额外多一份截图快照。

## Overview 页面能看到什么

- **总用例数 / 通过数 / 失败数 / 通过率**：Allure 自带的 Statistics 图表（甜甜圈图），
  不需要写代码，跑完 `pytest` 生成报告就有
- **按接口维度的用例数**：点开 **Behaviors** 标签页，就是 Epic → Feature → Story
  三层树，每层都带通过/失败统计；Overview 页面右侧的 Suites 迷你面板点进去也是
  同样的分组（因为 `@allure.suite`/`@allure.parent_suite` 也设成了跟 Feature 一致的名字）

## 已发现的接口小坑（写用例时踩过，供参考）

- `pageNo`/`pageSize` 缺省时后端会用 schema 里的 `default` 值兜底，不会报“必填缺失”，
  所以「未登录 + 缺省分页参数」会先被鉴权拦住返回 `2113`；但如果显式传了违反
  `minimum`/`maximum` 的值（如 `pageSize=0`），会被参数校验拦住返回 `2110`
  （消息文案是复用了“登录信息已过期”，实际含义是参数非法，不要被文案误导）
- 写涉及 `set_token(...)` 的反向用例时，`api_client` fixture 必须是 **function 级别**，
  不能是 session 级别，否则一个用例改了 Token 会污染同一 session 内后面用例的鉴权状态
  （踩过这个坑，已在 `testcases/conftest.py` 里修复并写了注释）
- OpenAPI 文档里 `loginId` 等 int64 字段标的是 `integer`，但后端实测会序列化成字符串
  （避免超出 JS 安全整数范围导致精度丢失），`utils/schema_validator.py` 里已经对
  `format: int64` 字段放宽为同时容忍字符串类型

## OpenAPI 文档

`openapi/wali_openapi.json` 是从 `https://manager-test.wali.network/app/v3/api-docs` 拉取的缓存，
`utils/schema_validator.py` 会基于这份文档对接口响应做 JSON Schema 校验。这份文档体积较大
（约 1MB）且会完整暴露被测系统的内部接口结构，**没有提交到仓库**，需要在本地执行一次：

```bash
python openapi/fetch_openapi.py
```

之后可随时重新运行该命令刷新到最新版本。

## 常用命令

```bash
./run_tests.sh                            # 跑全部用例 + 生成报告 + 自动打开浏览器
./run_tests.sh testcases/test_login.py    # 只跑登录接口
./run_tests.sh -m smoke                   # 只跑冒烟用例
./run_tests.sh -m negative                # 只跑反向用例
./run_tests.sh --no-open                  # 只生成报告，不自动打开浏览器

pytest -m needs_auth            # 只想单独跑 pytest 而不生成/打开报告时用
```

`--no-open` 之外的参数会原样传给 `pytest`，所以 `pytest` 支持的参数（`-k`、`-m`、文件路径等）都能用。
即使有用例失败，脚本也会继续生成报告，方便看失败详情和失败截图。

## 依赖

- `pytest` / `requests` / `allure-pytest` —— 测试框架、HTTP 客户端、报告生成
- `python-dotenv` —— 从 `.env` 加载配置
- `jsonschema` —— 基于 OpenAPI 文档做响应结构校验
- `Pillow` —— 失败截图（把请求/响应渲染成 PNG 图片）
- `PyMySQL` / `cryptography` —— 邮箱验证码登录用例读取测试库

完整版本号见 `requirements.txt`。

## License

[MIT](LICENSE)
