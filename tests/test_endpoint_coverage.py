"""端点覆盖守护 —— 拉 /openapi.json 比对 SDK 方法（防"API 加了端点、SDK 忘了补"）

⚠️ 需要网络；离线自动 skip（不误报）。
"""
import json
import urllib.request

import pytest

from ashareapi.client import AShareAPI

OPENAPI = "https://api.ashareapi.com/openapi.json"


def _spec():
    try:
        req = urllib.request.Request(OPENAPI, headers={"User-Agent": "sdk-test/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:                                     # 离线/网络问题 → skip
        pytest.skip("拉不到 openapi：%r" % (e,))


def _method_name(path: str) -> str:
    """端点路径 → SDK 方法名（`-` → `_`）"""
    return path.rstrip("/").rsplit("/", 1)[-1].replace("-", "_")


def test_every_endpoint_has_method():
    spec = _spec()
    missing = []
    for path in spec.get("paths", {}):
        name = _method_name(path)
        if not callable(getattr(AShareAPI, name, None)):
            missing.append("%s → %s()" % (path, name))
    assert not missing, "SDK 缺方法（新端点未补？）：%s" % missing


def test_coverage_ratio_is_full():
    spec = _spec()
    paths = list(spec.get("paths", {}))
    hit = sum(1 for p in paths if callable(getattr(AShareAPI, _method_name(p), None)))
    assert hit == len(paths), "只覆盖 %d/%d" % (hit, len(paths))
    assert len(paths) >= 30, "端点数异常：%d" % len(paths)
