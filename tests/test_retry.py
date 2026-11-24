"""429 重试行为（零网络 —— 用假 requests 拦输入输出）

行为约定：**按服务端返回的 ``Retry-After`` 决定是否重试**。
    要求等待 > ``RETRY_429_MAX_WAIT``(5s) ⇒ 不重试、立即抛 ``RateLimitError``；
    等待很短时才睡等重试。盲目退避会撞上同一个限流窗口，并把一次调用放大成多次请求。
"""
import pytest

from ashareapi import AShareAPI, RateLimitError
from ashareapi.client import RETRY_429_MAX_WAIT


class _FakeResp:
    def __init__(self, status_code, headers=None, payload=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._payload = payload if payload is not None else {}
        self.text = ""


def _patch(monkeypatch, headers, calls):
    import ashareapi.client as c

    def fake_request(*a, **k):
        calls["n"] += 1
        return _FakeResp(429, headers, {"detail": "slow down"})

    monkeypatch.setattr(c.requests, "request", fake_request)
    monkeypatch.setattr(c.time, "sleep", lambda *a, **k: None)   # 不真睡


def test_retry_after_long_no_retry(monkeypatch):
    """429 + ``Retry-After: 60`` ⇒ **只发 1 次**就抛（不盲目重试）。"""
    calls = {"n": 0}
    _patch(monkeypatch, {"Retry-After": "60"}, calls)
    with pytest.raises(RateLimitError):
        AShareAPI(api_key="k", retries=3).quote("sh600667")
    assert calls["n"] == 1


def test_retry_after_missing_still_retries(monkeypatch):
    """429 但**没有** ``Retry-After`` ⇒ 按 ``retries`` 次数重试。"""
    calls = {"n": 0}
    _patch(monkeypatch, {}, calls)
    with pytest.raises(RateLimitError):
        AShareAPI(api_key="k", retries=3).quote("sh600667")
    assert calls["n"] == 3


def test_retry_after_short_still_retries(monkeypatch):
    """429 + ``Retry-After`` 很短（≤ 上限）⇒ 睡等后仍重试。"""
    calls = {"n": 0}
    _patch(monkeypatch, {"Retry-After": str(RETRY_429_MAX_WAIT)}, calls)
    with pytest.raises(RateLimitError):
        AShareAPI(api_key="k", retries=2).quote("sh600667")
    assert calls["n"] == 2


def test_retry_after_parsing_tolerates_garbage():
    """``Retry-After`` 是 HTTP-date 或垃圾值 ⇒ 当 0，不崩。"""
    from ashareapi.client import _retry_after_seconds
    assert _retry_after_seconds(None) == 0
    assert _retry_after_seconds("") == 0
    assert _retry_after_seconds("60") == 60
    assert _retry_after_seconds(" 60 ") == 60
    assert _retry_after_seconds("Wed, 21 Oct 2026 07:28:00 GMT") == 0
