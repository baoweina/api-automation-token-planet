#!/usr/bin/env bash
# 一键跑接口自动化用例 + 生成/打开 Allure 报告。
#
# 用法：
#   ./run_tests.sh                       # 跑全部用例
#   ./run_tests.sh testcases/test_login.py   # 只跑某个文件
#   ./run_tests.sh -m negative           # 只跑反向用例（支持任意 pytest 参数）
#
# 加 --no-open 可以只生成报告不自动打开浏览器：
#   ./run_tests.sh --no-open -m smoke
set -euo pipefail
cd "$(dirname "$0")"

OPEN_REPORT=1
ARGS=()
for arg in "$@"; do
  if [[ "$arg" == "--no-open" ]]; then
    OPEN_REPORT=0
  else
    ARGS+=("$arg")
  fi
done

if [[ -f .venv/bin/activate ]]; then
  source .venv/bin/activate
fi

echo "==> 运行用例：pytest ${ARGS[*]:-}"
pytest "${ARGS[@]:-}" || true   # 即使有失败用例也继续生成报告

echo "==> 生成 Allure 报告"
allure generate reports/allure-results -o reports/allure-report --clean

REPORT_INDEX="$(pwd)/reports/allure-report/index.html"
echo "==> 报告已生成：${REPORT_INDEX}"

if [[ "$OPEN_REPORT" == "1" ]]; then
  echo "==> 用 allure open 启动本地服务并打开报告（Ctrl+C 结束）"
  allure open reports/allure-report
fi
