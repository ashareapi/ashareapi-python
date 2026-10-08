"""股票代码格式归一化 —— 兼容多种写法，统一成 API 原生格式（sh600667）

支持：
    sh600667      原生（沪）
    sz000001      原生（深）
    600667.SH     通用后缀风格（市场后缀）
    000001.SZ     通用后缀风格
    600667        纯 6 位（按首位推断：5/6→沪 0/3→深 4/8→北）
    hk00700 / usAAPL  原样返回（前缀小写化）
"""
from __future__ import annotations

import re

_SUFFIX = re.compile(r"^(\d{6})\.(SH|SZ|BJ)$", re.I)
_PREFIX = re.compile(r"^(SH|SZ|BJ|HK|US)(.+)$", re.I)
_BARE = re.compile(r"^\d{6}$")


def normalize_code(code: str) -> str:
    """把各种代码写法统一成 API 原生格式；认不出来就原样返回（让 API 报错，不猜）"""
    c = (code or "").strip()
    if not c:
        return c

    m = _SUFFIX.match(c)                       # 600667.SH → sh600667
    if m:
        return m.group(2).lower() + m.group(1)

    m = _PREFIX.match(c)                       # SH600667 → sh600667（前缀小写，后缀原样）
    if m:
        return m.group(1).lower() + m.group(2)

    if _BARE.match(c):                         # 纯 6 位 → 按首位推断市场
        if c[0] in "56":
            return "sh" + c
        if c[0] in "03":
            return "sz" + c
        if c[0] in "48":
            return "bj" + c
    return c
