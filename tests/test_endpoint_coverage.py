"""端点覆盖检查 —— 拉 /openapi.json 比对 SDK 方法（防止「API 加了端点、SDK 忘了补」）

⚠️ 需要网络；离线自动 skip（不误报）。
"""
import json
import urllib.request

import pytest

from ashareapi.client import AShareAPI

OPENAPI = "https://api.ashareapi.com/openapi.json"

# 不提供 SDK 方法的端点（需要时直接调 HTTP）。
#   列在这里的端点不参与「每个端点都有对应方法」的比对；
#   但它们必须仍然存在于线上 openapi（见 test_exempt_list_is_live）。
EXEMPT: dict[str, str] = {
    "/v1/wiki": "文档检索（字段单位与含义说明，不是取数接口）",
}

# 带路径参数的端点 —— 方法名不能由路径推导，需要显式对应。
ALIAS: dict[str, str] = {
    "/v1/agent-research/{task_id}": "agent_research_status",
}


def _spec():
    try:
        req = urllib.request.Request(OPENAPI, headers={"User-Agent": "sdk-test/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:                                     # 离线/网络问题 → skip
        pytest.skip("拉不到 openapi：%r" % (e,))


def _method_name(path: str) -> str:
    """端点路径 → SDK 方法名。

    多段路径**保留全部段**（`/v1/watchlist/quotes` → `watchlist_quotes`）——
    只取末段会得到 `quotes` / `snapshots` / `completions` 这种太泛、容易和别的端点混淆的名字。
    """
    segs = [s for s in path.strip("/").split("/") if s and s != "v1"]
    return ALIAS.get(path) or "_".join(segs).replace("-", "_")


def test_every_endpoint_has_method():
    spec = _spec()
    missing = []
    for path in spec.get("paths", {}):
        if path in EXEMPT:
            continue
        name = _method_name(path)
        if not callable(getattr(AShareAPI, name, None)):
            missing.append("%s → %s()" % (path, name))
    assert not missing, "SDK 缺方法（新端点未补？）：%s" % missing


def test_coverage_ratio_is_full():
    spec = _spec()
    paths = [p for p in spec.get("paths", {}) if p not in EXEMPT]
    hit = sum(1 for p in paths if callable(getattr(AShareAPI, _method_name(p), None)))
    assert hit == len(paths), "只覆盖 %d/%d" % (hit, len(paths))
    assert len(paths) >= 100, "端点数异常（openapi 可能没返回完整）：%d" % len(paths)


def test_exempt_list_is_live():
    """EXEMPT 里的端点必须仍然真实存在（端点改名 / 删除后，这里的例外就成了摆设）。"""
    spec = _spec()
    gone = [p for p in EXEMPT if p not in spec.get("paths", {})]
    assert not gone, "EXEMPT 里的端点已不存在，请清理：%s" % gone
