"""纯单测（零网络）—— 代码归一化 / 信封 → DataFrame 转换 / 无 Key 守卫"""
import pytest

from ashareapi import AShareAPI, AuthError
from ashareapi._code import normalize_code


def test_normalize_native():
    assert normalize_code("sh600667") == "sh600667"
    assert normalize_code("sz000001") == "sz000001"
    assert normalize_code("hk00700") == "hk00700"
    assert normalize_code("usAAPL") == "usAAPL"


def test_normalize_suffix_style():
    assert normalize_code("600667.SH") == "sh600667"
    assert normalize_code("000001.SZ") == "sz000001"
    assert normalize_code("830799.BJ") == "bj830799"


def test_normalize_bare_six():
    assert normalize_code("600667") == "sh600667"
    assert normalize_code("000001") == "sz000001"
    assert normalize_code("830799") == "bj830799"


def test_normalize_passthrough_garbage():
    assert normalize_code("") == ""
    assert normalize_code("not-a-code") == "not-a-code"   # 认不出就不猜，让 API 报错


def test_frame_structured_wins():
    cli = AShareAPI()
    b = {"ok": True, "data": "**markdown**", "structured": [{"a": 1}, {"a": 2}]}
    r = cli._frame(b)
    n = len(r)
    assert n == 2                                          # DataFrame 或 list[dict] 都可


def test_frame_array():
    cli = AShareAPI()
    r = cli._frame({"ok": True, "data": [{"x": 1}]})
    assert len(r) == 1


def test_frame_non_table_passthrough():
    cli = AShareAPI()
    assert cli._frame({"ok": True, "data": "纯文本"}) == "纯文本"
    assert cli._frame({"ok": True, "data": {"k": "v"}}) == {"k": "v"}


def test_frame_table_list_not_wrapped():
    """表列表（/v1/finance）→ 原样返回 list[list[dict]]，**不套 DataFrame**"""
    cli = AShareAPI()
    tabs = [[{"EndDate": "2026-06-30", "OperatingRevenue": 1}],
            [{"EndDate": "2026-06-30", "TotalAssets": 2}]]
    r = cli._frame({"ok": True, "data": tabs})
    assert r == tabs
    assert isinstance(r[0], list)          # 仍是表列表，不是 DataFrame


def test_frame_sectioned_dict_passthrough():
    """多段结构（/v1/shareholder、/v1/calendar）→ 原样返回 dict（含 tables/data）"""
    cli = AShareAPI()
    sec = {"tables": [{"title": "十大股东", "slug": "top10_holders", "rows": [{"name": "A"}]}],
           "data": {"top10_holders": [{"name": "A"}]}}
    assert cli._frame({"ok": True, "data": sec}) == sec


def test_raw_mode_returns_envelope():
    cli = AShareAPI(raw=True)
    b = {"ok": True, "data": [{"x": 1}], "elapsed_ms": 12}
    assert cli._frame(b) is b


def test_paid_endpoint_without_key_raises():
    """付费端点无 Key → 请求前就抛 AuthError（不发网络请求）"""
    cli = AShareAPI()
    with pytest.raises(AuthError):
        cli._request("/v1/finance", code="sh600667")


def test_frame_returns_body_when_no_data_field():
    """health / challenge 这类无 data 字段的端点 → 返回整个信封（不是 None）"""
    cli = AShareAPI()
    b = {"uptime_s": 12, "data_ready": True}
    assert cli._frame(b) == b


def test_ok_absent_is_not_failure():
    """只有**显式** ok=false 才算失败（无 ok 字段的工具端点不能被误判）"""
    import inspect
    from ashareapi.client import AShareAPI as _C
    assert 'body.get("ok") is False' in inspect.getsource(_C._request)


def test_free_endpoints_constant():
    """免 Key 端点清单（无 Key 守卫依赖它）：5 数据端点 + health/challenge 两个工具端点"""
    from ashareapi.client import FREE_ENDPOINTS
    assert len(FREE_ENDPOINTS) == 7
    for p in ("/v1/quote", "/v1/kline", "/v1/hot", "/v1/market-overview", "/v1/changedist",
              "/v1/health", "/v1/challenge"):
        assert p in FREE_ENDPOINTS


def test_empty_result_distinct_from_upstream():
    """ok=false + 空容器 → EmptyResultError（与"取数失败"区分）"""
    import inspect
    from ashareapi.client import AShareAPI as _C
    src = inspect.getsource(_C._request)
    assert "EmptyResultError" in src
    assert "data == []" in src


def test_empty_result_subclass_and_export():
    import ashareapi
    assert issubclass(ashareapi.EmptyResultError, ashareapi.AShareError)
    assert "EmptyResultError" in ashareapi.__all__
