"""核心客户端 —— 认证 / 请求 / 重试 / 信封解析 / 端点方法"""
from __future__ import annotations

import os
import time

import requests

from ._code import normalize_code
from .errors import APIError, AuthError, EmptyResultError, RateLimitError, UpstreamError

# 版本号单一事实源（`__init__.py` 从这里 re-export；User-Agent 也用它）
__version__ = "0.1.9"

DEFAULT_BASE = "https://api.ashareapi.com"
FREE_ENDPOINTS = (
    "/v1/quote", "/v1/kline", "/v1/hot", "/v1/market-overview", "/v1/changedist",  # 数据端点
    "/v1/health", "/v1/challenge",                                                # 工具端点
)


class AShareAPI:
    """A股数据 API 客户端

    :param api_key: API Key（默认读环境变量 ``ASHARE_API_KEY``；**免费端点可不传**）
    :param base_url: 服务地址（默认官方 ``https://api.ashareapi.com``）
    :param timeout: 单请求超时（秒）
    :param retries: ``429``/``5xx``/网络错误的**重试次数**（指数退避 0.5s/1.5s/4s）
    :param raw: ``True`` → 返回**原始信封** dict（含 ``endpoint/tier/elapsed_ms/source``），不转 DataFrame
    """

    def __init__(self, api_key: str | None = None, base_url: str = DEFAULT_BASE,
                 timeout: int = 30, retries: int = 3, raw: bool = False):
        self.api_key = (api_key or os.environ.get("ASHARE_API_KEY", "") or "").strip()
        self.base_url = (base_url or DEFAULT_BASE).rstrip("/")
        self.timeout = timeout
        self.retries = max(1, int(retries))
        self.raw = raw

    # ── 内部 ──────────────────────────────────────────────
    def _request(self, path: str, **params) -> dict:
        params = {k: v for k, v in params.items() if v not in (None, "")}
        headers = {"User-Agent": "ashareapi-python/%s" % __version__}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        elif path not in FREE_ENDPOINTS:
            raise AuthError(
                "端点 %s 需要 API Key（免 Key 端点：%s）。获取：https://ashareapi.com/pricing"
                % (path, " / ".join(FREE_ENDPOINTS)))
        last_err = None
        for i in range(self.retries):
            try:
                r = requests.get(self.base_url + path, params=params, headers=headers,
                                 timeout=self.timeout)
            except requests.RequestException as e:
                last_err = APIError("网络错误：%r" % (e,))
                time.sleep(0.5 * (3 ** i))
                continue
            if r.status_code == 401:
                raise AuthError("Key 无效或未携带（401）—— 检查 ASHARE_API_KEY")
            if r.status_code == 429:
                last_err = RateLimitError(
                    "超频（429）：降频重试；或解一次 PoW 挑战提额到 60 次/分"
                    "（GET /v1/challenge）；或升级档位")
                time.sleep(0.5 * (3 ** i))
                continue
            if r.status_code >= 500:
                last_err = APIError("服务端 %s" % r.status_code)
                time.sleep(0.5 * (3 ** i))
                continue
            try:
                body = r.json()
            except ValueError:
                raise APIError("响应不是 JSON（HTTP %s）：%s" % (r.status_code, r.text[:120]))
            # 只有**显式** ok=false 才算失败（服务端已自动处理，不扣调用次数）→ 重试无意义
            # health / challenge 这类工具端点没有 ok 字段 → 不能误判为失败
            if body.get("ok") is False:
                data = body.get("data")
                # 空容器 = "当前无数据"（如当天无大宗交易）→ 与"取数失败"区分开
                if data is None or data == [] or data == {}:
                    raise EmptyResultError(
                        "当前无数据（非失败）：%s —— 不计费，稍后重试或换条件"
                        % body.get("endpoint", path))
                raise UpstreamError(str(data or "上游取数失败（已自动换源，重试一次通常可好）"))
            return body
        raise last_err or APIError("重试 %d 次仍失败" % self.retries)

    def _frame(self, body: dict):
        """统一信封 → ``pandas.DataFrame``（未装 pandas 则退回 ``list[dict]``）

        端点 ``data`` 有两种形态：直接是数组，或是 Markdown 但附带 **``structured``** 结构化
        数组 → 这里**零 Markdown 解析** ✓

        ⚠️ **三种返回形态，不能一律套 DataFrame**：
          · 单表（多数端点）→ ``DataFrame``（未装 pandas → ``list[dict]``）
          · **表列表**（``/v1/finance``：``[[利润表行],[资产负债行],[现金流行]]``）
            → 返回**列表**（``list[list[dict]]``，对齐 JS SDK 的 ``Row[][]``）。
          · **多段结构**（``/v1/shareholder``、``/v1/calendar``：``{tables, data}``）
            → 原样返回该 dict（与 JS SDK 一致）。
        """
        if self.raw:
            return body
        rows = body.get("structured")
        if rows is None and isinstance(body.get("data"), list):
            rows = body["data"]
        if rows is None:
            return body.get("data", body)      # 无表格字段（health / challenge / usage）→ 返回整个信封
        # 表列表（首元素是 list）→ 不套 DataFrame，原样返回
        if rows and isinstance(rows[0], list):
            return rows                        # list[list[dict]]，对齐 JS SDK 的 Row[][]
        try:
            import pandas as pd
            return pd.DataFrame(rows)
        except ImportError:
            return rows                        # 未装 pandas 同样可用

    def _get(self, path: str, **params):
        return self._frame(self._request(path, **params))

    # ── 端点方法（32 个 —— 签名对齐 /openapi.json）─────────────────────
    # 【基础 / 工具】
    def health(self):
        """服务健康检查（数据源就绪状态）"""
        return self._get("/v1/health")

    def usage(self):
        """查询自身用量与额度"""
        return self._get("/v1/usage")

    def challenge(self, difficulty: int = 0):
        """获取 PoW 挑战（**匿名提额**：解出后单次请求带 ``X-PoW`` 头，额度 5/分 → 60/分）"""
        return self._get("/v1/challenge", difficulty=difficulty)

    # 【行情】
    def quote(self, code: str):
        """实时行情快照。``code``: ``sh600667`` / ``000001.SZ`` / ``600667``"""
        return self._get("/v1/quote", code=normalize_code(code))

    def kline(self, code: str, period: str = "day", count: int = 30):
        """K 线。``period``: ``day`` | ``week`` | ``month``

        ⚠️ 价格口径**固定为前复权**（除权除息日不跳空；**没有** ``adjust`` 参数）
        —— **不要再自己复权**（会二次复权）。
        """
        return self._get("/v1/kline", code=normalize_code(code), period=period, count=count)

    def hot(self, limit: int = 30):
        """全市场热搜榜"""
        return self._get("/v1/hot", limit=limit)

    def market_overview(self, type: str = "summary"):
        """市场总览。``type``: ``summary`` | ``trade`` | ``interval`` | ``technical`` | ``valuation`` | ``rotation``"""
        return self._get("/v1/market-overview", type=type)

    def changedist(self):
        """涨跌分布（市场广度）"""
        return self._get("/v1/changedist")

    # 【财务 / 公司】
    def finance(self, code: str, num: int = 4):
        """三大报表（利润表 / 资产负债表 / 现金流量表）"""
        return self._get("/v1/finance", code=normalize_code(code), num=num)

    def profile(self, code: str):
        """公司简况（上市日期 / 主营业务 / 行业）"""
        return self._get("/v1/profile", code=normalize_code(code))

    def dividend(self, code: str, years: int = 3):
        """分红送转历史"""
        return self._get("/v1/dividend", code=normalize_code(code), years=years)

    def shareholder(self, code: str):
        """股东研究（十大股东 / 股东户数 / 机构持仓）"""
        return self._get("/v1/shareholder", code=normalize_code(code))

    def chip(self, code: str):
        """筹码分布 / 成本"""
        return self._get("/v1/chip", code=normalize_code(code))

    def orderbook(self, code: str):
        """五档盘口 order book（买一~买五 / 卖一~卖五）

        **秒级快照，盘中才有意义**（收盘后为当日最后快照）；量单位 = **手**（×100 = 股）。
        字段对齐 Tushare 惯例：``b1_p``/``b1_v`` ~ ``b5_p``/``b5_v``（买档价格/量）、
        ``a1_p``/``a1_v`` ~ ``a5_p``/``a5_v``（卖档）→ 装了 pandas 时可直接 ``df["b1_p"]``。
        跌停时买档全 0 / 涨停时卖档全 0（正常现象）。
        """
        return self._get("/v1/orderbook", code=normalize_code(code))

    def snapshot(self, code: str):
        """全字段行情画像（价格 + 盘口 + 估值 + 市值 + 股本 + 涨停跌停价 + 量比 + 振幅 + 涨速）

        ⚠️ **与 `quote()` 的分工**：`quote()` 轻（8 字段，**免费**）；本方法全（24+ 字段，**付费**）
        —— **只要现价用 `quote()` 更轻（字段少、响应快）**。
        ⚠️ **仅 A 股**（港股/美股字段布局不同，用 `quote()`）—— **传其他市场返回空，不返回错数据**。
        **计费 = 次数**：本方法 1 次拿全 24+ 字段 —— **要估值+市值+股本+涨停价多项时，比分别调 quote/valuation/orderbook 更省次数**（3 次 → 1 次）。
        单位：``amount`` 万元 · ``volume`` 手 · 市值 亿元 · 股本 股 · 比率 百分数。
        """
        return self._get("/v1/snapshot", code=normalize_code(code))

    def events(self, code: str):
        """个股事件标签（42 类）"""
        return self._get("/v1/events", code=normalize_code(code))

    # 【资金 / 交易】
    def fund(self, code: str):
        """个股资金 + 龙虎榜 + 大宗 + 两融（综合，一接口全有）"""
        return self._get("/v1/fund", code=normalize_code(code))

    def lhb(self, type: str = "institution", date: str = ""):
        """龙虎榜分榜。``type``: ``institution``（机构）| ``hotmoney``（游资）| ``activeseat``（活跃席位）"""
        return self._get("/v1/lhb", type=type, date=date)

    def margin_trade(self, code: str = "", date: str = ""):
        """融资融券明细。``code`` 留空 = 全市场"""
        return self._get("/v1/margin-trade", code=normalize_code(code), date=date)

    def block_trade(self, code: str = "", date: str = ""):
        """大宗交易。``code`` 留空 = 全市场"""
        return self._get("/v1/block-trade", code=normalize_code(code), date=date)

    # 【指标 / 选股】
    def technical(self, code: str):
        """技术指标：MA / MACD / KDJ / RSI / BOLL"""
        return self._get("/v1/technical", code=normalize_code(code))

    def screen(self, expr: str = "", preset: str = "", limit: int = 20, orderby: str = "",
               desc: bool = True, market: str = ""):
        """因子选股。``expr`` 如 ``"intersect([PE_TTM > 0, PE_TTM < 20, ROETTM > 15])"``；``preset`` 如 ``low_pe``"""
        return self._get("/v1/screen", expr=expr, preset=preset, limit=limit, orderby=orderby,
                         desc=str(bool(desc)).lower(), market=market)

    # 【板块 / 产业链】
    def sector(self):
        """板块行情榜（行业 / 概念 / 地域 + 领涨股）"""
        return self._get("/v1/sector")

    def sector_valuation(self, code: str):
        """板块估值（PE/PB/PS + 历史百分位）。``code`` 如 ``pt01801780``"""
        return self._get("/v1/sector-valuation", code=normalize_code(code))

    def industry_chain(self, mode: str = "graph", topic: str = "", code: str = ""):
        """产业链。``mode``: ``list``（主题清单）| ``graph``（图谱，配 ``topic``）| ``stock``（个股定位，配 ``code``）"""
        return self._get("/v1/industry-chain", mode=mode, topic=topic, code=normalize_code(code))

    # 【宏观 / 固收 / ETF / 新股】
    def macro(self, region: str = "cn", names: str = ""):
        """宏观数据。``region``: ``cn`` | ``us`` | ``jp`` | ``eu`` | ``hk``"""
        return self._get("/v1/macro", region=region, names=names)

    def bond(self, code: str):
        """可转债条款（溢价率 / 双低 / 强赎触发 / 评级）"""
        return self._get("/v1/bond", code=normalize_code(code))

    def etf(self, code: str):
        """ETF 概览（行情 / 规模 / 折溢价 / 资金流）"""
        return self._get("/v1/etf", code=normalize_code(code))

    def ipo(self, days: int = 15):
        """新股日历（发行 / 申购 / 中签 / 上市）"""
        return self._get("/v1/ipo", days=days)

    # 【日历 / 研报 / 搜索】
    def calendar(self, date: str = "", limit: int = 20):
        """投资日历（个股事件：分红派息 / 解禁 / 财报）"""
        return self._get("/v1/calendar", date=date, limit=limit)

    def dehydrated(self, mode: str = "list", symbol: str = "", limit: int = 10):
        """脱水研报。``mode``: ``list`` | ``detail``（配 ``symbol``）"""
        return self._get("/v1/dehydrated", mode=mode, symbol=symbol, limit=limit)

    def search(self, q: str):
        """搜索股票 / 基金 / 板块（消歧）"""
        return self._get("/v1/search", q=q)
