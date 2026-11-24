"""4xx（除 401/429）必须抛异常，不能把服务端的错误内容当成正常返回值。

行为约定：
    · 4xx 一律抛 ``AuthError``（403）或 ``APIError``（其余），消息里带服务端原话；
    · 4xx 不重试（重试不会成功，只会增加请求量）。

三种常见 4xx（都是请求本身需要调整，不是网络问题）：
  · ``413`` —— ``/v1/kline`` 单次「标的数 × count」超 60000（如 200 只 × 1212）
  · ``403`` —— 分钟线但档位 < standard
  · ``422`` —— 匿名单次 > 5 只标的 / ``period`` 取值非法

零网络：打桩 ``requests.request``。
"""
import pandas as pd
import pytest

from ashareapi import APIError, AShareAPI, AuthError


class _FakeResp:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.headers = {}
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def _patch(monkeypatch, status_code, payload):
    import ashareapi.client as c

    calls = {"n": 0}

    def fake_request(*a, **k):
        calls["n"] += 1
        return _FakeResp(status_code, payload)

    monkeypatch.setattr(c.requests, "request", fake_request)
    monkeypatch.setattr(c.time, "sleep", lambda *a, **k: None)
    return calls


def _case(status_code, payload):
    return pytest.param(status_code, payload, id="HTTP_%d" % status_code)


# 错误体按服务端实际返回的形状构造
CASES = [
    _case(413, {"error": "单次预估 242,400 条，超过上限 60,000 条（标的 200 × count 1212）。"
                         "请拆分标的或减小 count",
                "limit_items": 60000, "est_items": 242400,
                "how_to": "把 code 拆成多次请求，或把 count 调小（本上限是防单请求过大）"}),
    _case(403, {"error": "分钟线需要 standard（当前 trial）—— 日 / 周 / 月线仍免费",
                "min_tier": "standard", "upgrade": "https://ashareapi.com/pricing"}),
    _case(422, {"error": "匿名单次最多 5 只标的（本次 100 只）；批量取数请申请 API Key",
                "max_codes": 5, "requested_codes": 100,
                "pricing": "https://ashareapi.com/pricing"}),
]


@pytest.mark.parametrize("status_code,payload", CASES)
def test_4xx_raises_instead_of_returning_dict(monkeypatch, status_code, payload):
    """4xx → 抛异常（403 归 AuthError，其余 APIError），且**消息里带服务端原话**。"""
    calls = _patch(monkeypatch, status_code, payload)
    expect = AuthError if status_code == 403 else APIError
    with pytest.raises(expect) as ei:
        AShareAPI(retries=1).kline("sh600000", count=1212)
    assert payload["error"] in str(ei.value)          # ⛔ 不吞掉服务端写的可读原因
    assert calls["n"] == 1                            # 4xx = 请求本身有问题 ⇒ 重试无意义


@pytest.mark.parametrize("status_code,payload", CASES)
def test_4xx_result_is_not_a_dict_crashing_dataframe(monkeypatch, status_code, payload):
    """回归锚点：**不会**返回"转 DataFrame 会报错"的字典。"""
    _patch(monkeypatch, status_code, payload)
    try:
        got = AShareAPI(retries=1).kline("sh600000", count=1212)
    except (AuthError, APIError):
        return                                        # ✅ 期望路径
    pytest.fail(
        "4xx 返回了 %r —— 应当抛 AuthError / APIError" % (got,))


def test_422_fastapi_validation_body_is_flattened(monkeypatch):
    """FastAPI 参数校验体（``{"detail": [{...,"msg": "…"}]}``）→ 取到 ``msg``。"""
    _patch(monkeypatch, 422, {"detail": [
        {"loc": ["query", "period"], "msg": "周期不支持；可选：day / week / month", "input": "weekly"}]})
    with pytest.raises(APIError) as ei:
        AShareAPI(retries=1).kline("sh600000", period="weekly")
    assert "周期不支持" in str(ei.value)


def test_ok_200_still_returns_dataframe(monkeypatch):
    """反向保护：正常 200 **不受影响**，仍是 DataFrame（8 列 K 线）。"""
    _patch(monkeypatch, 200, {
        "ok": True, "endpoint": "kline", "tier": "free", "elapsed_ms": 735, "source": "multi",
        "data": [{"date": "2026-10-19", "open": "9.72", "last": "9.80", "high": "9.82",
                  "low": "9.65", "volume": "336462", "amount": "328491284", "turnover": "0.10"}],
    })
    df = AShareAPI(retries=1).kline("sh600000", count=1)
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["date", "open", "last", "high", "low",
                                "volume", "amount", "turnover"]


def test_raw_true_still_returns_envelope(monkeypatch):
    """反向保护：``raw=True`` 仍是整个信封 dict（向后兼容，行为不变）。"""
    env = {"ok": True, "endpoint": "kline", "tier": "free", "elapsed_ms": 1,
           "source": "multi", "data": []}
    _patch(monkeypatch, 200, env)
    assert AShareAPI(retries=1, raw=True).kline("sh600000") == env
