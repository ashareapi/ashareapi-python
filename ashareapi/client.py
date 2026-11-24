"""核心客户端 —— 认证 / 请求 / 重试 / 信封解析 / 端点方法"""
from __future__ import annotations

import os
import time
import warnings

import requests

from ._code import normalize_code
from .errors import APIError, AuthError, EmptyResultError, RateLimitError, UpstreamError

# 版本号单一事实源（`__init__.py` 从这里 re-export；User-Agent 也用它）
__version__ = "0.3.1"

DEFAULT_BASE = "https://api.ashareapi.com"

# 匿名档"安全轮询间隔"（秒）—— 匿名限 5 次/分 ⇒ 12s。仅用于过密提示。
#    只提示，不做限速/延迟（SDK 不改变调用行为）。
ANON_SAFE_INTERVAL = 12.0
FREE_ENDPOINTS = (
    "/v1/quote", "/v1/kline", "/v1/hot", "/v1/market-overview", "/v1/changedist",  # 数据端点
    "/v1/wiki",                                                                   # 文档检索（免费）
    "/v1/trade-calendar", "/v1/models",                                           # 交易日历 / 模型清单（免费）
    "/v1/health", "/v1/challenge",                                                # 工具端点
)
# 429 退避上限：服务端返 ``Retry-After: 60``（每分钟窗口）⇒ 若要求等待超过这个秒数，
# 盲目重试只会把 1 次调用放大成 N 次，且必然再撞 429。
# ⇒ 只有「服务端要求等待很短」时才睡等重试；否则立即抛出，由调用方决定何时再来。
RETRY_429_MAX_WAIT = 5


def _retry_after_seconds(value) -> int:
    """解析 ``Retry-After`` 响应头（秒数形式）。HTTP-date 形式或缺失 → 返回 ``0``。"""
    if not value:
        return 0
    try:
        return max(0, int(float(str(value).strip())))
    except (TypeError, ValueError):
        return 0


def _server_error_text(r) -> str:
    """从 **4xx 响应体**里取出服务端写给人看的那句话（``error`` / ``detail``）。

    服务端 4xx 的形状有两种：
      · 业务错误：``{"error": "单次预估 242,400 条，超过上限 60,000 条…", ...}``
      · 参数校验（FastAPI）：``{"detail": [{"loc": ["query","period"], "msg": "周期不支持；可选：…"}]}``
    取不到就退回响应原文（截断 120 字）—— **宁可糙也不要吞掉**。
    """
    try:
        body = r.json()
    except Exception:
        return str(getattr(r, "text", ""))[:120]
    if isinstance(body, dict):
        msg = body.get("error") or body.get("detail")
        if isinstance(msg, str) and msg.strip():
            return msg.strip()
        if isinstance(msg, list):                      # FastAPI 校验错误
            parts = []
            for item in msg:
                if isinstance(item, dict):
                    parts.append(str(item.get("msg") or item))
                else:
                    parts.append(str(item))
            if parts:
                return "; ".join(parts)
    return str(getattr(r, "text", ""))[:120]


class AShareAPI:
    """A股数据 API 客户端

    :param api_key: API Key（默认读环境变量 ``ASHARE_API_KEY``；**免费端点可不传**）
    :param base_url: 服务地址（默认官方 ``https://api.ashareapi.com``）
    :param timeout: 单请求超时（秒）
    :param retries: ``5xx`` / 网络错误的**重试次数**（指数退避 0.5s / 1.5s / 4s）。
        ``429`` **另有一套**：服务端返 ``Retry-After`` 且等待 > 5s 时**不重试**、直接抛
        :class:`RateLimitError`（避免把 1 次调用放大成 N 次、且必然再撞限流）。
    :param raw: ``True`` → 返回**原始信封** dict（含 ``endpoint/tier/elapsed_ms/source``），不转 DataFrame
    """

    def __init__(self, api_key: str | None = None, base_url: str = DEFAULT_BASE,
                 timeout: int = 30, retries: int = 3, raw: bool = False):
        self.api_key = (api_key or os.environ.get("ASHARE_API_KEY", "") or "").strip()
        self.base_url = (base_url or DEFAULT_BASE).rstrip("/")
        self.timeout = timeout
        self.retries = max(1, int(retries))
        self.raw = raw
        self._last_ts = 0.0          # 上次请求时刻（"轮询过密"提示用）

    # ── 请求层工具 ──────────────────────────────────────────────
    def _request(self, path: str, _method: str = "GET", _json=None, **params) -> dict:
        params = {k: v for k, v in params.items() if v not in (None, "")}
        # 轮询节奏提示：匿名档 5 次/分 ⇒ 间隔 <12s 会撞 429。
        #    只 `warnings.warn` 一次、**不 delay 不拦截**（SDK 绝不改调用行为）。
        _now = time.time()
        if not self.api_key and self._last_ts and (_now - self._last_ts) < ANON_SAFE_INTERVAL:
            warnings.warn(
                "调用间隔仅 %.1fs —— 匿名档限 5 次/分，建议轮询间隔 ≥12s"
                "（解一次 PoW 挑战可到 15 次/分 ≈ ≥4s）；过密会收到 429 并白耗调用。"
                "配 API Key 后 standard 档 120 次/分：https://ashareapi.com/pricing"
                % (_now - self._last_ts), RuntimeWarning)
        self._last_ts = _now
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
                _kw = {"params": params, "headers": headers, "timeout": self.timeout}
                if _json is not None:
                    _kw["json"] = _json
                r = requests.request(_method, self.base_url + path, **_kw)
            except requests.RequestException as e:
                last_err = APIError("网络错误：%r" % (e,))
                time.sleep(0.5 * (3 ** i))
                continue
            if r.status_code == 401:
                raise AuthError("Key 无效或未携带（401）：%s" % _server_error_text(r))
            if r.status_code == 429:
                wait = _retry_after_seconds(r.headers.get("Retry-After"))
                last_err = RateLimitError(
                    "超频（429）：%s；或解一次 PoW 挑战提额到 15 次/分"
                    "（GET /v1/challenge，只提每分钟次数）。若提示为每日条数用尽，"
                    "解 PoW 无效 —— 次日恢复或用 Key"
                    % (("服务端要求 %d 秒后再试" % wait) if wait else "已被限流"))
                # 服务端给了 Retry-After（通常 60s）⇒ 窗口远大于退避上限 ⇒ **不再重试**，
                #    立即抛出（盲目重试必然再撞，且把请求量放大）。
                if wait > RETRY_429_MAX_WAIT:
                    raise last_err
                if i == self.retries - 1:
                    break
                time.sleep(wait or 0.5 * (3 ** i))
                continue
            if r.status_code >= 500:
                last_err = APIError("服务端 %s" % r.status_code)
                time.sleep(0.5 * (3 ** i))
                continue
            # 其余 4xx（403 / 413 / 422 …）必须抛错，不能当成功返回。
            # 服务端 4xx 的错误体没有 data 字段，当结果返回会让 DataFrame 转换失败，
            # 而且把失败原因吞掉。4xx = 请求本身有问题 ⇒ 重试无意义，立即抛出并带上服务端原话。
            # 403 = 无权限（档位不够）→ 归 AuthError。
            if r.status_code >= 400:
                raise (AuthError if r.status_code == 403 else APIError)(
                    "HTTP %s：%s" % (r.status_code, _server_error_text(r)))
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
                raise UpstreamError(str(data or "数据源取数失败（已自动换源，重试一次通常可好）"))
            return body
        raise last_err or APIError("重试 %d 次仍失败" % self.retries)

    def _frame(self, body: dict):
        """统一信封 → ``pandas.DataFrame``（未装 pandas 则退回 ``list[dict]``）

        端点 ``data`` 有两种形态：直接是数组，或是 Markdown 但附带 **``structured``** 结构化
        数组 → 这里**零 Markdown 解析** ✓

        **三种返回形态，不能一律套 DataFrame**：
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

    def _post(self, path: str, json_body=None, **params):
        return self._frame(self._request(path, _method="POST", _json=json_body, **params))

    def _delete(self, path: str, **params):
        return self._frame(self._request(path, _method="DELETE", **params))

    # ── 端点方法（签名对齐 /openapi.json）─────────────────────
    # 【基础 / 工具】
    def health(self):
        """服务健康检查（数据源就绪状态）"""
        return self._get("/v1/health")

    def usage(self):
        """查询自身用量与额度"""
        return self._get("/v1/usage")

    def challenge(self, difficulty: int = 0):
        """获取 PoW 挑战（**匿名提额**：解出后单次请求带 ``X-PoW`` 头，额度 5/分 → 15/分；**只提每分钟次数，每日条数上限不变**）"""
        return self._get("/v1/challenge", difficulty=difficulty)

    # 【行情】
    def quote(self, code: str):
        """实时行情快照。``code``: ``sh600667`` / ``000001.SZ`` / ``600667``"""
        return self._get("/v1/quote", code=normalize_code(code))

    def kline(self, code: str, period: str = "day", count: int = 30,
              start: str = "", end: str = ""):
        """K 线。``period``: ``day`` | ``week`` | ``month`` | ``season`` | ``year``
        | ``m1`` | ``m5`` | ``m15`` | ``m30`` | ``m60`` | ``m120``

        :param start: 起始日期 ``YYYY-MM-DD``（**仅 day 与分钟线支持**；须与 ``end`` 配对；
            传了它 ``count`` 被忽略，默认取满 1212 条。港股/美股/期货/外汇不支持）
        :param end: 结束日期 ``YYYY-MM-DD``（同 ``start``）

        复权口径**由服务端写死**，没有 ``adjust`` 参数：日线及以上为**前复权**（除权除息日
        不跳空），分钟线为**不复权** —— **不要再自己复权**（会二次复权）。
        分钟线（``m*``）属**付费层**，**必须同时传 start 与 end**（窗口近 1 个月），
        且不支持 北交所 / 期货 / 外汇；要全历史分钟请用专业数据商。
        """
        kw = dict(code=normalize_code(code), period=period, count=count)
        if start:
            kw["start"] = start
        if end:
            kw["end"] = end
        return self._get("/v1/kline", **kw)

    def kline_full(self, code: str, fq: str = "qfq", start: str = "", end: str = ""):
        """**全历史**日线一次拿全（约 2,500 根 · 2016-08-08 起），是 :meth:`kline` 的超集。

        :param fq: 复权口径 —— ``qfq`` 前复权（默认，画图用）| ``hfq`` 后复权
            （**回测用** —— 历史不随未来分红变化，可复现）| ``nofq`` 不复权（自己算复权）
        :param start: 起始日期 ``YYYY-MM-DD``（可省略；须与 ``end`` 配对使用）
        :param end: 结束日期 ``YYYY-MM-DD``（可省略）

        **仅 A 股个股**（``sh``/``sz``/``bj``）；ETF / 可转债 / 指数 / 板块 / 港美股 /
        期货 / 外汇**不支持** —— 那些用 :meth:`kline`。
        固定 7 列（``time`` ``open`` ``high`` ``low`` ``close`` ``volume`` ``amount``），
        无 ``turnover`` 换手率。属**付费层**（standard 起）。
        """
        kw = dict(code=normalize_code(code), fq=fq)
        if start:
            kw["start"] = start
        if end:
            kw["end"] = end
        return self._get("/v1/kline-full", **kw)

    def minute(self, code: str, days: int = 1):
        """分时（当日 / 近 5 日盘中走势）。``days``: ``1``（当日，默认）| ``5``（近 5 个交易日）

        与 :meth:`kline` 的分钟线**不是一回事**：``kline`` 给分钟 **K 线**（OHLC 蜡烛），
        本方法是**分时**（每分钟一个价 + 累计量）。
        付费层；``days`` **只有 1 和 5 两档**（传其他值会按 5 日返回）。
        """
        return self._get("/v1/minute", code=normalize_code(code), days=days)

    def hot(self, limit: int = 30, type: str = "stock"):
        """全市场热搜榜。``type``: ``stock`` | ``wx`` | ``news`` | ``sector`` | ``etf``"""
        return self._get("/v1/hot", limit=limit, type=type)

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

    def chip(self, code: str, date: str = ""):
        """筹码分布 / 成本（套牢盘 / 获利盘比例，判断抛压）

        :param date: 交易日 ``YYYY-MM-DD``（缺省 = 最新）。**历史仅保留约近 1 年**；
            更早的日期返回空结果（``ok:false``，**不扣次数**）。非交易日 / 未来日期会
            **自动回退**到最近交易日 —— 以返回行的 ``date`` 字段为准，别假定它等于传入值。
        """
        return self._get("/v1/chip", code=normalize_code(code), date=date)

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

        **与 `quote()` 的分工**：`quote()` 轻（8 字段，**免费**）；本方法全（24+ 字段，**付费**）
        —— **只要现价用 `quote()` 更轻（字段少、响应快）**。
        **仅 A 股**（港股/美股字段布局不同，用 `quote()`）—— **传其他市场返回空，不返回错数据**。
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
    def technical(self, code: str, date: str = ""):
        """技术指标：MA / MACD / KDJ / RSI / BOLL。``date`` 留空取最新交易日"""
        return self._get("/v1/technical", code=normalize_code(code), date=date)

    def screen(self, expr: str = "", preset: str = "", limit: int = 20, orderby: str = "",
               desc: bool = True, market: str = "", *, mode: str = "", filters: str = "",
               sort: str = "", board: str = "", metric: str = "", pool: str = "",
               strategy: str = "", event: str = "", offset: int = 0, date: str = "",
               start: str = "", end: str = "", asset: str = "", list_: str = "",
               slim: bool = False):
        """因子选股 / 条件筛选（语义参数 —— 不用记数据源字段码）。

        推荐写法::

            cli.screen(preset="low_pe", sort="roe_ttm", limit=10)
            cli.screen(filters="pe_ttm:0..20,roe_ttm:>=15", board="hs300")
            cli.screen(mode="rank", metric="technical", limit=50)
            cli.screen(list_="fields")        # 94 个可用字段（带中文名与单位）

        ``filters`` 语法：逗号分隔＝AND；区间 ``0..20``（含两端）；
        比较支持 ``>=`` ``<=`` ``>`` ``<`` ``=``。
        ``sort`` 默认降序，``-`` 前缀＝升序（``sort="-roe_ttm"``）。
        ``board`` 可选 ``hs300`` / ``zz500`` / ``zz1000`` / ``sse50`` / ``sz_component``，不传＝全市场。

        旧参数 ``expr`` / ``orderby`` / ``desc`` / ``market`` **继续可用**（服务端兼容），
        新代码请改用 ``filters`` / ``sort`` / ``board``。
        """
        return self._get(
            "/v1/screen",
            expr=expr, preset=preset, limit=limit, orderby=orderby,
            desc=str(bool(desc)).lower(), market=market,
            mode=mode, filters=filters, sort=sort, board=board, metric=metric,
            pool=pool, strategy=strategy, event=event, offset=offset or "",
            date=date, start=start, end=end, asset=asset, list=list_,
            slim=str(bool(slim)).lower() if slim else "",
        )

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
    def macro(self, region: str = "cn", names: str = "", limit: int = 12):
        """宏观数据。``region``: ``cn`` | ``us`` | ``jp`` | ``eu`` | ``hk``；``limit`` = 每个指标最多 N 条"""
        return self._get("/v1/macro", region=region, names=names, limit=limit)

    def bond(self, code: str):
        """可转债条款（溢价率 / 双低 / 强赎触发 / 评级）"""
        return self._get("/v1/bond", code=normalize_code(code))

    def etf(self, code: str, kind: str = "概览", start: str = "", end: str = "",
            date: str = ""):
        """ETF 数据。``kind`` 选子集：

        ``概览``（默认，行情 / 规模 / 折溢价 / 资金流 / 回撤 / 估值）
        | ``详情``（基金要素 / 费率 / 份额）| ``持仓``（成分股及权重）
        | ``净值``（历史**单位净值**，4 位小数）| ``公司``（管理人 / 托管人 / 跟踪指数）
        | ``持有人``（户数 / 机构个人占比）| ``财务``（股 / 债 / 商品 / 基金占比）

        :param kind: 子集选择，**传中文值**（7 选 1）
        :param start: 仅 ``kind=净值``：起始日期 ``YYYY-MM-DD``（**须与 end 配对**）
        :param end: 仅 ``kind=净值``：结束日期 ``YYYY-MM-DD``
        :param date: 仅 ``kind=概览`` / ``kind=持仓``：**历史快照日** ``YYYY-MM-DD``
            （概览＝那天的折溢价/规模/估值百分位；持仓＝那天的重仓股）。留空＝最新。

        **单次只查 1 只**：``code`` 传逗号会 422，多只请分别调用（每只独立计次）。
        **仅 ETF 代码**：传个股代码返回 ``ok:false``（**不扣次数**），不会给全 0 空壳 ——
        代码不确定请先用 :meth:`search` 或 ``hot(type="etf")`` 确认。
        代码可传裸 6 位（``510300``）或带前缀（``sh510300``）。
        ``kind=净值`` 的 ``nav`` 是**真实单位净值**，不是收盘价（跨境 / 商品 ETF 两者可能差 10% 以上）。
        多表结果（``详情`` 3 表 / ``公司`` 2 表）需要 ``raw=True`` 拿 ``tables`` 才全。
        历史快照的两个数据源边界：**未来日期按最近交易日返回**（看返回的 ``date`` 列自证）；
        **上市前日期回全 0**（会被拦成 ``ok:false``）。``kind=持仓`` 不传 ``date`` 时是 **Top20**，
        传 ``date`` 时是两段（重仓股涨跌 + 申赎清单前 10）。
        """
        return self._get("/v1/etf", code=normalize_code(code),
                         kind=kind, start=start, end=end, date=date)

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

    # 【量化】回测 / 批量回测 / 策略清单 / 因子库 / 方法论库
    #    这几个端点属**付费层**（standard 起；批量回测 pro 起），且计入**重型日额度**。
    def backtest(self, strategy: str = "buy_hold", mode: str = "single", code: str = "",
                 start: str = "2019-01-01", end: str = "", initial_cash: float = 1_000_000,
                 weighting: str = "equal", include_equity: bool = False):
        """量化回测。``mode``: ``single``（单标的实时，配 ``code``）| ``portfolio``（组合，查预置区间）。

        ``weighting`` 仅 ``mode=portfolio`` 有效：``equal``（等权）| ``inv_vol``（波动率倒数，不限量版）。
        """
        return self._get("/v1/backtest", strategy=strategy.lower(), mode=mode.lower(),
                         code=normalize_code(code) if code else "", start=start, end=end,
                         initial_cash=initial_cash, weighting=weighting.lower(),
                         include_equity=str(bool(include_equity)).lower())

    def backtest_batch(self, codes, strategies="buy_hold", start: str = "2019-01-01",
                       end: str = "", initial_cash: float = 1_000_000):
        """批量回测（多标的 × 多策略对比矩阵）。``codes`` / ``strategies`` 可为列表或逗号分隔字符串。

        上限：标的 ≤ 20 · 策略 ≤ 10 · 组合 ≤ 60（超限直接报错，不静默截断）。属 **pro** 档。
        """
        cs = codes if isinstance(codes, str) else ",".join(codes)
        ss = strategies if isinstance(strategies, str) else ",".join(strategies)
        return self._get("/v1/backtest-batch", codes=cs, strategies=ss,
                         start=start, end=end, initial_cash=initial_cash)

    def strategies(self):
        """量化策略清单（20 条单标的择时 + 9 条组合选股，含参数范围）。不占重型额度。"""
        return self._get("/v1/strategies")

    def factors(self, category: str = "", kind: str = ""):
        """量化因子库（87 因子 + 50 筛选入口 + 22 预设）。不占重型额度。

        ``category`` / ``kind`` **只接受中文枚举值**：
        ``估值``/``行情``/``盈利``/``资产负债``/``现金流``；``排行``/``标签``/``事件``。
        """
        return self._get("/v1/factors", category=category, kind=kind)

    def playbooks(self, category: str = "", id: str = ""):
        """量化方法论库（25 条「怎么判断市场」流程，含判据 / 阶段 / 实测证据）。不占重型额度。"""
        return self._get("/v1/playbooks", category=category, id=id)

    # 【短线打板】涨停池 / 复盘 / 异动 / 集合竞价
    #    均属 **standard（¥29.9）** 起。
    def auction(self, code: str, mode: str = "stock", date: str = ""):
        """**集合竞价**（个股 9:15–9:25）。``mode``: ``stock``（当日竞价分时，默认）|
        ``stock-history``（历史**秒级**分时，须配 ``date``）| ``volume``（当日竞价量 / 资金净额）。

        顶层含**「竞价触及涨停」判定**与 ``up_px`` / ``down_px`` / ``open_px`` 等。
        ``mode=stock`` **仅当日**（数据源限制）；查历史用 ``stock-history`` + ``date``（须真实交易日）。
        """
        return self._get("/v1/auction", code=normalize_code(code), mode=mode, date=date)

    def limit_up(self, mode: str = "limit", date: str = ""):
        """**打板**：当日涨停股 + **涨停原因** + 资金面。

        ``mode``:
          · ``limit``（默认）涨停池明细 —— 当日**全部**涨停股。
          · ``auction`` 竞价涨停 —— 只留「**09:25 定盘即封在涨停价**」的票（一字板 / 竞价抢筹），
            盘前最常看的一张表。竞价中摸过涨停、但定盘前被砸开的票**不算**
            （它们开盘后才重封，``limit_time`` 给的是重封时刻，如 09:30）。

        字段含 ``streak`` 连板数 / ``limit_time`` 涨停时间(Unix 秒) / ``reason`` 涨停原因 /
        ``seal_amount`` 封单额 / ``main_net`` 主力净额 / ``concepts`` 概念 / ``turnover`` 换手%。
        ``date`` = 取该交易日历史；留空 = 实时（须真实交易日，非交易日返空）。
        """
        return self._get("/v1/limit-up", mode=mode, date=date)

    def review(self, mode: str = "board", date: str = ""):
        """**短线复盘（涨停结构）**。``mode``: ``board``（板块主线，默认）| ``ladder``（连板梯队）。

        ``board`` = 当日涨停最集中的题材板块（``limit_count`` 涨停数 / ``amount`` 成交额 / ``stocks`` 成分股）；
        ``ladder`` = 按连板高度分组的涨停个股（``streak`` / ``market_cap`` / ``tips`` 如「7天4板」）。
        ``date`` = 取该交易日历史；留空 = 实时。
        """
        return self._get("/v1/review", mode=mode, date=date)

    def abnormal(self, mode: str = "deviation", date: str = "", limit: int = 600):
        """**监管异动 / 偏离值**（短线风控关键信号）。``mode``: ``deviation``（偏离值热门榜，今日实时，
        默认）| ``deviation_hist``（历史，须配 ``date``）| ``deviation_plan``（今日 + 明日两组）|
        ``abnormal``（异动频率）等。

        字段含 ``reason`` 规则 / ``pct`` 涨幅 / ``turnover`` 换手 / ``board_desc`` 连板 / ``concepts`` 概念。
        ``limit`` 1–2000（默认 600）。
        """
        return self._get("/v1/abnormal", mode=mode, date=date, limit=limit)

    # 【全市场 / 批量】
    #    均属 **pro（¥99）** 起，且计入**重型日额度**。
    def market_kline(self, date: str, limit: int = 0, offset: int = 0, codes: str = ""):
        """**全市场单日 K 线**：一次返回某交易日全 A 股（5000+ 只）的日线。

        :param date: 交易日 ``YYYY-MM-DD``（**必填**）
        :param limit: 分页条数（``0`` = 全部）
        :param offset: 分页偏移
        :param codes: 只取指定股票（逗号分隔），留空 = 全市场

        **仅 pro / unlimited**；**1 次调用折算 500 次额度**，另有独立日额度（pro 200 / unlimited 1000）。
        仅 A 股股票（5572 只 · 2016-08-08 起）· **不复权原始价**；最新到**前一交易日**。约 785 KB/次。
        """
        return self._get("/v1/market-kline", date=date, limit=limit, offset=offset, codes=codes)

    def fund_batch(self, codes):
        """**批量资金流**：一次拿多只股票的资金流（主力资金 + 龙虎榜 + 大宗 + 两融），每只一条。

        :param codes: 股票代码（列表或**逗号分隔**字符串，如 ``"sh600519,sz000001"``）

        **仅 pro / unlimited**；单次上限 pro **200** 只 / unlimited **1000** 只。
        **计费按实际返回只数**（失败的**不计**）。资金流仅覆盖 A 股。
        """
        cs = codes if isinstance(codes, str) else ",".join(codes)
        return self._get("/v1/fund-batch", codes=cs)

    # 【资讯 / 公告】
    #    均属 **standard（¥29.9）** 起。分工：``news`` = 时效 · ``notice`` = 历史（可回溯约 16 年）。
    def news(self, code: str = "", id: str = "", limit: int = 50, type: str = ""):
        """**个股 / 指数 / ETF / 板块 / 转债资讯**。**不传 ``id``** ⇒ 列表（``code`` 必填）；
        **传 ``id``** ⇒ 该条**完整正文**（干净 Markdown，可直接喂大模型）。

        列表**只有最新 N 条**（数据源无翻页 / 历史）；要历史用 :meth:`notice`。
        列表里的 ``url`` 指向动态页、**抓不到正文** ⇒ 要正文必须用 ``id``。
        """
        return self._get("/v1/news", code=normalize_code(code), id=id, limit=limit, type=type)

    def notice(self, code: str = "", id: str = "", type: str = "", limit: int = 50, offset: int = 0):
        """**上市公司公告**。**不传 ``id``** ⇒ 列表（``code`` 必填，可翻页，回溯约 **16 年**）；
        **传 ``id``** ⇒ 详情。

        详情两种形态：多数（短公告）⇒ ``text`` = 正文纯文本；少数（长报告 100+ 页）⇒
        ``text`` 空、``url`` = **PDF 链接** ⇒ 判据 = **先看 ``text`` 有没有值**，空则取 ``url`` 自行解析。
        💡 要财务数字用 :meth:`finance`。
        """
        return self._get("/v1/notice", code=normalize_code(code), id=id, type=type,
                         limit=limit, offset=offset)

    # 【元信息 / 工具】
    def models(self):
        """OpenAI / Anthropic 兼容模型清单（免费）"""
        return self._get("/v1/models")

    def trade_calendar(self, date: str = "", start: str = "", end: str = "", year: str = "", trading_only: bool = False, limit: int = 0, offset: int = 0):
        """交易日历（开市/休市 · 年末最后交易日）"""
        return self._get("/v1/trade-calendar", date=date, start=start, end=end, year=year, trading_only=trading_only, limit=limit, offset=offset)

    # 【AI Agent / 协议兼容】
    def agent_search(self, q: str, scope: str = "", depth: str = "fast", max_results: int = 10, clarify: bool = False, claim: str = "", replay: bool = False, authority_min: float = 0.0, recency: str = ""):
        """自然语言受控检索（带证据链 · 供开发者编排）"""
        return self._get("/v1/agent-search", q=q, scope=scope, depth=depth, max_results=max_results, clarify=clarify, claim=claim, replay=replay, authority_min=authority_min, recency=recency)

    def agent_ask(self, q: str, scope: str = "", max_results: int = 10, recency: str = ""):
        """自然语言问答（带内联引用 · BYOK：用你自己的模型 key）"""
        return self._post("/v1/agent-ask", q=q, scope=scope, max_results=max_results, recency=recency)

    def messages(self, payload: dict):
        """Anthropic Messages 协议（Claude Code / Anthropic SDK · BYOK）"""
        return self._post("/v1/messages", json_body=payload)

    # 【自选股】
    def watchlist(self, action: str = "list", code: str = "", codes="", list_name: str = "", name: str = "", note: str = "", tags: str = ""):
        """自选股（列表 / 添加 / 删除）"""
        _c = normalize_code(code)
        _cs = codes if isinstance(codes, str) else ",".join(codes)
        return self._get("/v1/watchlist", action=action, code=_c, codes=_cs, list=list_name, name=name, note=note, tags=tags)

    def watchlist_import(self, payload: dict):
        """自选股导入（CSV / JSON）"""
        return self._post("/v1/watchlist", json_body=payload)

    def watchlist_quotes(self, list_name: str = ""):
        """自选股批量行情"""
        return self._get("/v1/watchlist/quotes", list=list_name)

    def scanner_snapshots(self, limit: int = 20):
        """选股员快照（按 Key 隔离 · 含前向收益汇总）"""
        return self._get("/v1/scanner/snapshots", limit=limit)

    def scanner(self, q: str):
        """选股员（scanner Agent · 条件选股 · 证据链 · 工具轨迹 · 专业版起）"""
        return self._get("/v1/scanner", q=q)

    def analyst(self, snapshot_id: str, focus: str = "overall", horizon: str = ""):
        """复盘分析师（读 scanner 快照 · 不选股 · 不预测）"""
        return self._get("/v1/analyst", snapshot_id=snapshot_id, focus=focus, horizon=horizon)

    def chat_completions(self, payload: dict):
        """OpenAI Chat Completions 协议（OpenAI SDK / 通用客户端 · BYOK）"""
        return self._post("/v1/chat/completions", json_body=payload)

    def responses(self, payload: dict):
        """OpenAI Responses API（Codex / openai SDK 2.x · BYOK）"""
        return self._post("/v1/responses", json_body=payload)

    def agent_research(self, q: str, depth: str = "standard"):
        """异步研究任务（提交 · 带引用报告 · BYOK）"""
        return self._post("/v1/agent-research", q=q, depth=depth)

    def agent_research_status(self, task_id: str):
        """查研究任务（进度 / 报告）。``task_id`` 来自 :meth:`agent_research` 的返回"""
        return self._get("/v1/agent-research/%s" % task_id)

    # 【其余数据 / 资金 / 指数】
    def futures(self, code: str):
        """外盘期货实时快照（买卖价 / 结算价 / 持仓变化 / 到期日）"""
        return self._get("/v1/futures", code=code)

    def forex(self, code: str):
        """外汇现货实时报价（买一卖一 / 涨跌幅 / 市场状态）"""
        return self._get("/v1/forex", code=code)

    # 【批量（一次多只）】
    def finance_batch(self, codes, periods: int = 4, type: str = "", fields: str = "all"):
        """批量财务报表（多只一次取）"""
        _cs = codes if isinstance(codes, str) else ",".join(codes)
        return self._get("/v1/finance-batch", codes=_cs, periods=periods, type=type, fields=fields)

    def technical_batch(self, codes, date: str = ""):
        """批量技术指标（多只一次取 · 55 项）"""
        _cs = codes if isinstance(codes, str) else ",".join(codes)
        return self._get("/v1/technical-batch", codes=_cs, date=date)

    def quote_batch(self, codes, period: str = "day", count: int = 1, start: str = "", end: str = ""):
        """批量行情（多只一次取）"""
        _cs = codes if isinstance(codes, str) else ",".join(codes)
        return self._get("/v1/quote-batch", codes=_cs, period=period, count=count, start=start, end=end)

    def kline_batch(self, codes, period: str = "day", count: int = 30, start: str = "", end: str = "", fq: str = ""):
        """批量 K 线（多只一次取）"""
        _cs = codes if isinstance(codes, str) else ",".join(codes)
        return self._get("/v1/kline-batch", codes=_cs, period=period, count=count, start=start, end=end, fq=fq)

    def snapshot_batch(self, codes):
        """批量全字段画像（多只一次取）"""
        _cs = codes if isinstance(codes, str) else ",".join(codes)
        return self._get("/v1/snapshot-batch", codes=_cs)

    def profile_batch(self, codes):
        """批量公司简况（多只一次取）"""
        _cs = codes if isinstance(codes, str) else ",".join(codes)
        return self._get("/v1/profile-batch", codes=_cs)

    def chip_batch(self, codes, date: str = ""):
        """批量筹码分布（多只一次取）"""
        _cs = codes if isinstance(codes, str) else ",".join(codes)
        return self._get("/v1/chip-batch", codes=_cs, date=date)

    def shareholder_batch(self, codes):
        """批量股东研究（多只一次取）"""
        _cs = codes if isinstance(codes, str) else ",".join(codes)
        return self._get("/v1/shareholder-batch", codes=_cs)

    # 【L2 大单 / 龙虎榜】
    def bigorder(self, code: str):
        """L2 大单净额分时（分钟级 · 机构版专属）"""
        _c = normalize_code(code)
        return self._get("/v1/bigorder", code=_c)

    def bigorder_flow(self, code: str, money: int = 0, limit: int = 100, offset: int = 0):
        """L2 大单成交明细（含主动/被动拆分 · 机构版专属）"""
        _c = normalize_code(code)
        return self._get("/v1/bigorder-flow", code=_c, money=money, limit=limit, offset=offset)

    def bigorder_flow_full(self, code: str, money: int = 0, max_rows: int = 6000):
        """L2 大单成交·全天完整（含主动/被动拆分 · 机构版专属）"""
        _c = normalize_code(code)
        return self._get("/v1/bigorder-flow-full", code=_c, money=money, max_rows=max_rows)

    def bigorder_queue(self, code: str, vol: int = 500, tur: int = 30, limit: int = 100):
        """L2 大单委托流（挂单 + 撤单标记 · 机构版专属）"""
        _c = normalize_code(code)
        return self._get("/v1/bigorder-queue", code=_c, vol=vol, tur=tur, limit=limit)

    def bigorder_history(self, code: str, limit: int = 100):
        """L2 历史大单净额（逐日 · 最多 100 个交易日 · 机构版专属）"""
        _c = normalize_code(code)
        return self._get("/v1/bigorder-history", code=_c, limit=limit)

    def bigorder_split(self, code: str, date: str = ""):
        """L2 主力四分解（分钟级 · 主动/被动 × 买/卖 · 机构版专属）"""
        _c = normalize_code(code)
        return self._get("/v1/bigorder-split", code=_c, date=date)

    def bigorder_rank(self, sort: str = "net_in", limit: int = 100, offset: int = 0, date: str = ""):
        """L2 全市场主力净额榜（5568 只 · 8 种排序 · 机构版专属）"""
        return self._get("/v1/bigorder-rank", sort=sort, limit=limit, offset=offset, date=date)

    def lhb_seats(self, code: str, date: str = ""):
        """龙虎榜席位明细（营业部 · 游资标记 · 机构版专属）"""
        _c = normalize_code(code)
        return self._get("/v1/lhb-seats", code=_c, date=date)

    def lhb_agency(self, date: str = "", sort: str = "net_buy", limit: int = 100):
        """龙虎榜机构参与个股榜（全市场 · 机构买入/卖出 · 机构版专属）"""
        return self._get("/v1/lhb-agency", date=date, sort=sort, limit=limit)

    # 【情绪 / 事件 / 榜单】
    def market_mood(self, date: str = ""):
        """市场情绪（破板率 + 赚钱效应 9 日趋势）"""
        return self._get("/v1/market-mood", date=date)

    def limit_reason(self, code: str, date: str = "", limit: int = 20):
        """涨停原因（某只票的历史涨停记录 + 完整原因文案）"""
        _c = normalize_code(code)
        return self._get("/v1/limit-reason", code=_c, date=date, limit=limit)

    def broken_board(self, date: str = "", limit: int = 100):
        """炸板历史（某日炸板股清单 + 概念）"""
        return self._get("/v1/broken-board", date=date, limit=limit)

    def tail_chase(self, limit: int = 300, sort: str = "chase_amount"):
        """尾盘抢筹（全市场 · 抢筹金额榜）"""
        return self._get("/v1/tail-chase", limit=limit, sort=sort)

    def northbound(self, date: str = "", limit: int = 50):
        """A 股北向资金分板块持仓（季度）"""
        return self._get("/v1/northbound", date=date, limit=limit)

    def new_high(self, date: str = "", limit: int = 50):
        """百日新高（按题材汇总）"""
        return self._get("/v1/new-high", date=date, limit=limit)

    def flash(self, limit: int = 50, index: int = 0):
        """7×24 财经快讯（全市场电报）"""
        return self._get("/v1/flash", limit=limit, index=index)

    def evidence(self, q: str, scope: str = "notice,news", limit: int = 10):
        """财经多源取证（公告 + 资讯 · 带证据指纹）"""
        return self._get("/v1/evidence", q=q, scope=scope, limit=limit)

    def index_constituent(self, code: str):
        """指数成分股（沪深300 等 · 全量清单）"""
        _c = normalize_code(code)
        return self._get("/v1/index-constituent", code=_c)

    def suspension(self, market: str = "沪深"):
        """停复牌列表（沪深 / 港股 / 美股）"""
        return self._get("/v1/suspension", market=market)

    def buyback(self, code: str, start: str = "", end: str = ""):
        """公司回购（A股 / 港股）"""
        _c = normalize_code(code)
        return self._get("/v1/buyback", code=_c, start=start, end=end)

    def consensus(self, codes):
        """一致预期（目标价 + 未来盈利预测）"""
        _cs = codes if isinstance(codes, str) else ",".join(codes)
        return self._get("/v1/consensus", codes=_cs)

    def rating(self, codes):
        """机构评级（港股 / 美股 · 目标价 + 评级分布）"""
        _cs = codes if isinstance(codes, str) else ",".join(codes)
        return self._get("/v1/rating", codes=_cs)

    def disclosure(self, codes):
        """财报披露日历（业绩预约披露日）"""
        _cs = codes if isinstance(codes, str) else ",".join(codes)
        return self._get("/v1/disclosure", codes=_cs)

    def fund_flow(self, code: str, start: str = "", end: str = ""):
        """个股资金流向（A股 / 港股；沪深支持历史区间）"""
        _c = normalize_code(code)
        return self._get("/v1/fund-flow", code=_c, start=start, end=end)

    def fund_short(self, code: str, date: str = ""):
        """卖空数据（港股 / 美股）"""
        _c = normalize_code(code)
        return self._get("/v1/fund-short", code=_c, date=date)

    def fund_south(self, codes, date: str = ""):
        """南下资金持仓（港股通 · 季度）"""
        _cs = codes if isinstance(codes, str) else ",".join(codes)
        return self._get("/v1/fund-south", codes=_cs, date=date)

    def index_list(self, limit: int = 50, offset: int = 0, date: str = ""):
        """指数清单（1223 个 · 含港股指数）"""
        return self._get("/v1/index-list", limit=limit, offset=offset, date=date)

    def score(self, codes, date: str = ""):
        """股票评分（五维 · 含周月季变动）"""
        _cs = codes if isinstance(codes, str) else ",".join(codes)
        return self._get("/v1/score", codes=_cs, date=date)

    def report(self, code: str = "", id: str = "", limit: int = 20, offset: int = 0):
        """研报（列表 / 全文）"""
        _c = normalize_code(code)
        return self._get("/v1/report", code=_c, id=id, limit=limit, offset=offset)

    def stocks(self, market: str = "", industry: str = "", limit: int = 0, offset: int = 0):
        """全市场股票清单（代码 / 名称 / 上市日期 / 行业）"""
        return self._get("/v1/stocks", market=market, industry=industry, limit=limit, offset=offset)

    # 【Key 管理】IP 白名单
    def ip_whitelist(self, action: str = "get", ips=""):
        """**IP 白名单**（把 Key 锁定到固定 IP，外泄也用不了）。属 **Unlimited** 档。

        :param action: ``get``（查当前名单）| ``set``（设置，整体替换，配 ``ips``）|
            ``clear``（清空，恢复任意 IP 可用）
        :param ips: 仅 ``action="set"`` 需要 —— IP 列表（列表或逗号分隔字符串，≤50，
            **精确 IPv4/IPv6**，不支持网段）

        设置后**只有名单内的 IP 能调用该 Key**（含本方法自身）⇒ 换网络时请把新旧 IP
        **一起传**。若已把自己锁死，请联系客服（管理员通道解除）。
        """
        if action == "get":
            return self._get("/v1/ip-whitelist")
        if action == "clear":
            return self._delete("/v1/ip-whitelist")
        if action == "set":
            s = ips if isinstance(ips, str) else ",".join(ips)
            return self._post("/v1/ip-whitelist", ips=s)
        raise ValueError("action 只支持 get / set / clear（当前：%r）" % (action,))
