<div align="center">

<a href="https://ashareapi.com/en/"><img src="https://ashareapi.com/icon-512.png" width="88" height="88" alt="ashareapi"></a>

# ashareapi — Official Python SDK for the A-Share Data API

**Quotes (intraday line · five-level depth) / K-lines / Financials / Money flow / Dragon-Tiger list / L2 order flow / Sectors / Factor screening / Quant backtest / short-term board plays / call auction / news & filings** — **102 endpoints**, and the **free endpoints require no sign-up**.

![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python\&logoColor=white)

![pandas](https://img.shields.io/badge/pandas-supported-150458?logo=pandas\&logoColor=white)

![PyPI](https://img.shields.io/pypi/v/ashareapi?label=PyPI)

![CI](https://github.com/ashareapi/ashareapi-python/actions/workflows/ci.yml/badge.svg)

![License](https://img.shields.io/badge/license-MIT-green)

[中文](README.md) · **English**

[Website](https://ashareapi.com/en/) · [Docs](https://ashareapi.com/en/docs/) · [Endpoint list](https://ashareapi.com/en/endpoints/) · [MCP](https://ashareapi.com/en/mcp/) · [Agent Skill](https://ashareapi.com/en/skill/)

[Source](https://github.com/ashareapi/ashareapi-python) · [Issues](https://github.com/ashareapi/ashareapi-python/issues) · [Changelog](https://ashareapi.com/en/changelog/)

</div>

Popular endpoint docs: [K-line](https://ashareapi.com/en/docs/endpoints/kline/) · [Factor screening](https://ashareapi.com/en/docs/endpoints/screen/) · [Health check](https://ashareapi.com/en/docs/endpoints/health/)

```bash
pip install ashareapi            # base (returns list[dict])
pip install "ashareapi[pandas]"  # adds DataFrame support (recommended)
```

> There is also a **Node.js / TypeScript SDK**: `npm install ashareapi` — [npm](https://www.npmjs.com/package/ashareapi)

## What this is

**The official Python SDK for the A-Share Data API** — one method call returns a `DataFrame`: URL building, retries, rate-limit backoff, typed errors and response shapes are already handled for you. After `pip install ashareapi`:

```python
from ashareapi import AShareAPI
cli = AShareAPI(api_key="ct-your-key")   # or set the ASHARE_API_KEY env var
print(cli.quote("sh600667"))             # quotes
print(cli.backtest(code="sh600667", strategy="mom20"))   # quant backtest
```

**10 endpoints need no key** (they work as soon as you install): `/v1/quote` · `/v1/kline` · `/v1/hot` · `/v1/market-overview` · `/v1/changedist` · `/v1/wiki` · `/v1/trade-calendar` · `/v1/models` · `/v1/health` · `/v1/challenge`. The rest need a key ([get one](https://ashareapi.com/en/pricing/), from ¥9.9).

## 30-second quickstart

```python
from ashareapi import AShareAPI

cli = AShareAPI()                     # free endpoints need no key
df = cli.quote("sh600667")            # last 30 trading days → DataFrame
print(df[["date", "last", "turnover"]])

print(cli.kline("600667.SH", count=5))  # any code format works (auto-normalized)
print(cli.hot(limit=10))                # hot-search ranking
```

**Paid endpoints** (financials / money flow / Dragon-Tiger list / screening, etc.) need a key — [get one](https://ashareapi.com/en/pricing/) from ¥9.9:

```python
cli = AShareAPI("ct-your-key")          # or set the ASHARE_API_KEY env var
df = cli.screen(preset="low_pe", sort="roe_ttm", limit=10)
print(df.head())
```

## Ways to connect (one key, six ways in)

Pick whatever your stack already uses — same key, same plan, nothing extra to buy:

| Way in | Install | Covers |
|---|---|---|
| **Python SDK** | `pip install ashareapi` | scripts / backtests / data pipelines |
| **Node.js / TS SDK** | `npm install ashareapi` | services / frontends / cron jobs |
| **MCP** | one URL: `https://api.ashareapi.com/mcp` | **19 clients** (Claude Code / Cursor / Codex / VS Code…) · **94 tools** |
| **Personal agents** | add MCP inside the assistant app | Today / Grok Bot / Muse / Dots / Duet |
| **Agent Skill** | drop into your skills directory | works with **45+ clients** |
| **Pi (pi.dev)** | `npm install ashareapi-pi` | query from inside Pi; knows which endpoint to call |
| **DSH plugin** | install the plugin | DeepSeek Harness |

All of these are native support, not a relay layer — same endpoints, same quota, same key. Details in the sections below.

## Why use it

- **No caching on intraday data**: every call re-fetches · `minute` intraday line (242 points per day) · `auction` call-auction series (09:15–09:25, ~150 points)
- **10 years of K-line history**: back to 2016-08-08, `kline_full` returns it in one call (~2,500 bars; each symbol starts at **its own listing date**, so a 2019 STAR-market listing has ~1,700); daily / weekly / monthly / quarterly / yearly + minute bars `m1`–`m120`, **forward-adjusted** (no `adjust` parameter, no double-adjust)
- **Whole-market in one call**: `market_kline` returns daily bars for **every A-share (5,000+) on a given trading day** — no 5,000-iteration loop (Pro and up; one call counts as 500 quota)
- **7 L2 microstructure endpoints**: market-wide main-force net-flow ranking **in one call (5,568 stocks)** · dragon-tiger seats **drilled to branch level** with an `is_youzi` flag · four-way large orders / add-cancel queue / 100-day large-order history
- **9 batch endpoints**: quotes / K-lines / snapshots / financials / technicals / chips / shareholders / money flow / company profile — **150 symbols in one call ≈ 2s** (200 one-by-one ≈ 5 min)
- **One key, five markets**: A-shares + on-exchange ETFs (1,716) + HK (22 endpoints) + US (16 endpoints) + futures & FX (65 symbols)
- **No code needed**: wire up MCP and just ask "how is Moutai doing today" — Claude Code / Cursor / Codex, plus personal agents such as Today / Grok Bot / Muse (**19 clients · 94 tools**)
- **Quant stack in one place**: 87 factors + 29 strategies + 25 playbooks + backtests (single / portfolio / batch) + portfolio weight optimisation
- **You are not charged for what you do not get**: empty results, failed fetches and mistyped codes cost **nothing** (billing follows rows actually returned)
- **10 endpoints need no key**: `quote / kline / hot / market-overview / changedist / wiki / trade-calendar / models / health / challenge` — no sign-up
- **Traceable failures**: every response carries a `trace_id`; quote it in a support request and we can look up that exact request
- **Clear error taxonomy**: 401 → `AuthError`, 429 → `RateLimitError`, failed fetch → `UpstreamError`, no data → `EmptyResultError` (**no data ≠ failure**) — all four are plain `except` branches
- **Ticker format tolerant**: `sh600667` / `600667.SH` / `600667` all accepted
- **Automatic source failover**: 70 data sources back each other up; a failed fetch switches source and **does not consume your quota**
- **pandas is optional**: works without pandas too (returns `list[dict]`)

## Endpoints

| Method                                   | Description                                                                                                  | Key-free |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------ | -------- |
| `quote(code)`                            | Last 30 trading days (one row per day)                                                                       | ✅        |
| `kline(code, period, count, start, end)` | K-line (daily / weekly / monthly / quarterly / yearly + minute bars `m1`–`m120`) · adjustment fixed server-side (qfq for daily and above · raw for minute bars) | ✅ daily and above / paid for minute bars |
| `minute(code, days)`                     | **Intraday tick chart** (today / last 5 sessions) · paid                                                      | —        |
| `hot(limit)`                             | Hot-search ranking                                                                                           | ✅        |
| `market_overview(type)`                  | Market overview (profile / valuation / style rotation)                                                       | ✅        |
| `changedist()`                           | Advance-decline distribution (market breadth)                                                                | ✅        |
| `finance(code, num)`                     | The three financial statements                                                                               | —        |
| `fund(code)`                             | Money flow + Dragon-Tiger list + block trades + margin trading                                               | —        |
| `technical(code)`                        | MA / MACD / KDJ / RSI / BOLL                                                                                 | —        |
| `lhb(type)`                              | Dragon-Tiger sub-rankings (institutions / hot money / active seats)                                          | —        |
| `screen(filters=, sort=, board=, mode=)` | Factor screening / conditional filter (semantic params; legacy `expr`/`orderby` still work)                  | —        |
| `search(q)`                              | Search with disambiguation                                                                                   | —        |
| `kline_full(code, fq, start, end)`                   | **Full-history** daily bars in one call (~2,465 rows) · `fq` is `qfq`/`hfq`/`nofq`                           | —        |
| `backtest(strategy, mode, code, ...)`    | **Quant backtest** (single stock live / portfolio preset ranges · `weighting` = equal or inverse-volatility) | —        |
| `backtest_batch(codes, strategies, ...)` | **Batch backtest** (many stocks × many strategies comparison matrix · ≤20 × 10)                              | —        |
| `strategies()`                           | Quant strategy list (20 single-stock + 9 portfolio, with parameter ranges)                                   | —        |
| `factors(category, kind)`                | Quant factor library (87 factors + 50 screening entries + 22 presets + 14 strategy templates)                                      | —        |
| `playbooks(category, id)`                | Quant playbook library (25 "how to judge the market" workflows)                                              | —        |
| `ip_whitelist(action, ips)`              | **IP allow-list** (lock a key to fixed IPs · `action` = get/set/clear)                                       | —        |


**The remaining endpoints**, grouped:

| Group | Methods |
|---|---|
| Batch (many symbols per call) | `quote_batch` · `kline_batch` · `snapshot_batch` · `profile_batch` · `finance_batch` · `technical_batch` · `chip_batch` · `shareholder_batch` |
| L2 order flow | `bigorder` · `bigorder_flow` · `bigorder_flow_full` · `bigorder_queue` · `bigorder_history` · `bigorder_split` · `bigorder_rank` |
| Dragon-tiger board | `lhb_seats` · `lhb_agency` |
| Sentiment / boards | `market_mood` · `limit_reason` · `broken_board` · `tail_chase` · `northbound` · `new_high` · `flash` |
| AI Agent | `agent_search` · `agent_ask` · `agent_research` · `agent_research_status` · `scanner` · `scanner_snapshots` · `analyst` · `evidence` |
| Watchlist | `watchlist` · `watchlist_import` · `watchlist_quotes` |
| Protocol-compatible | `messages` · `chat_completions` · `responses` (OpenAI / Anthropic clients, BYOK) |
| Futures / FX | `futures` · `forex` |
| Everything else | `models` · `trade_calendar` · `index_list` · `index_constituent` · `suspension` · `buyback` · `consensus` · `rating` · `disclosure` · `fund_flow` · `fund_short` · `fund_south` · `score` · `report` · `stocks` |
> **L2 microstructure (7 endpoints · Institutional tier)** — brokers call this layer "Level-2 enhanced" and usually sell the feed as a separate licence; here it is 7 method calls:
> - `bigorder_rank`: **market-wide main-force net-flow ranking — 5,568 stocks in one call**, 8 sort orders (not one symbol at a time)
> - `lhb_seats`: dragon-tiger seats **drilled down to branch level**, with an `is_youzi` (hot-money) flag
> - The other 5: intraday large-order net flow · tick-level four-way large orders · order add/cancel queue · 100-day large-order history · main-force four-way split

> **Batch endpoints (9)** — most APIs take one symbol per call, so 200 symbols means 200 round trips; here you pass many at once:
> - Covers: quotes / K-lines / snapshots / company profile / financials / technical indicators / chips / shareholders / money flow
> - Limits: 200 symbols per call on Pro · 1000 on Institutional
> - Billing: charged **per row actually returned** — failed symbols are not charged
> - Measured: 150 symbols of daily bars in one call ≈ 2s (200 symbols one-by-one ≈ 5 min); split 200 into 2 batches

> **K-line prices are always forward-adjusted (qfq)** — no gaps on ex-dividend dates, and there is **no** `adjust` parameter. **Do not adjust them yourself** (that would double-adjust).

(All 102 endpoints: [endpoint list](https://ashareapi.com/en/endpoints/))

## Return shapes

With `pandas` installed, methods return a **`DataFrame`** (otherwise `list[dict]`), so you can select columns by name:

```python
df = cli.quote("sh600667")
print(df[["date", "last", "turnover"]])
```

Use `raw=True` when you need the **raw envelope** (with `endpoint` / `tier` / `elapsed_ms` / `source`):

```python
cli = AShareAPI(raw=True)
env = cli.quote("sh600667")
# { 'ok': True, 'endpoint': '/v1/quote', 'tier': 'free', 'elapsed_ms': 862, 'source': '...', 'data': [...] }
```

> **Three return shapes**: most endpoints are a **single table** → `DataFrame`; `finance()` returns a **list of tables** (`list[list[dict]]`); `shareholder()` / `calendar()` return a **sectioned structure** (`{tables, data}`, kept as a plain dict). The latter two are **not** wrapped into a DataFrame.

## Error handling

```python
from ashareapi import AShareAPI, AuthError, RateLimitError, UpstreamError, EmptyResultError

cli = AShareAPI()
try:
    df = cli.fund("sh600667")
except AuthError as e:          # 401 / missing key → go get a key
    print(e)
except RateLimitError as e:     # 429 → slow down / solve the PoW challenge for a higher quota / upgrade
    print(e)
except UpstreamError as e:      # upstream fetch failed (source already switched, quota not charged) → one retry usually fixes it
    print(e)
except EmptyResultError as e:   # no data right now (e.g. no block trades today) → not billed; change conditions or retry later
    print(e)
```

> **`stale` is visible when you ask for the raw envelope**: with `raw=True`, a response that is not freshly fetched carries `stale: true` plus `stale_age_s` (seconds since the last good data) — old values are never returned silently.

## Other ways to connect

### MCP server

- Server URL **`https://api.ashareapi.com/mcp`** (use **that** endpoint URL; the site page `ashareapi.com/en/mcp/` is the **guide**, not the endpoint)
- **Per-client configuration** (Claude Code / Cursor / VS Code / Codex and **19 clients** in total, every key name checked against official docs): <https://ashareapi.com/en/mcp/>
- **Agent Skill** (an endpoint manual for AI Agents + a downloadable package; drop it into your skills directory): <https://ashareapi.com/en/skill/>

> Free tools/endpoints need **no key**; paid tools take `Authorization: Bearer <your-key>` in the request header.

### Personal agents (assistants on your phone)

No code: add one MCP entry inside the assistant app and ask for quotes, financials or K-lines.

| Assistant | Where to add it | Auth |
|---|---|---|
| **Today** | Settings → Connected apps → Add custom MCP | Bearer Token |
| **Grok Bot** | Connect apps → custom remote MCP | Bearer Header |
| **Muse** | Settings → Connectors → Custom Connector | Bearer / OAuth |
| **Dots** | Add a connector in ChatGPT first | Inherited from ChatGPT |
| **Duet** | Add a connector in Claude first | Inherited from Claude |

Same values everywhere:

```
URL:       https://api.ashareapi.com/mcp
Transport: Streamable HTTP
Auth:      Authorization: Bearer <your-key>
```

- Public HTTPS only — **localhost is not supported**
- In a "Bearer token" field, paste **the key only** (do not type `Bearer` again)
- Only fall back to `?key=` when the client cannot send headers

Once connected you can ask: "how is sh600519 doing", "give me the last 30 daily bars for 600519", "today's top 10 limit-up stocks by turnover".
Full walkthrough: <https://ashareapi.com/en/docs/guides/personal-agent/>

## Examples

Runnable examples live in [`examples/`](https://github.com/ashareapi/ashareapi-python/tree/main/examples):

| File                                                                                                       | What it does                                                                                                 |
| ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| [`examples/quickstart.py`](https://github.com/ashareapi/ashareapi-python/blob/main/examples/quickstart.py) | Fetch **quotes / K-lines / hot search** from free endpoints (no key) + commented examples for paid endpoints |


```bash
python examples/quickstart.py
```

## Requirements

- **Python ≥ 3.9**
- Only depends on [`requests`](https://pypi.org/project/requests/) (≥ 2.28)
- `pandas` optional: installed → returns `DataFrame`, not installed → returns `list[dict]`
- Example code: [`examples/quickstart.py`](https://github.com/ashareapi/ashareapi-python/blob/main/examples/quickstart.py)

## Related

**Official SDKs**: Python `pip install ashareapi` · Node.js / TypeScript `npm install ashareapi`

**MCP server**: `https://api.ashareapi.com/mcp` ([setup](https://ashareapi.com/en/mcp/))

**Agent Skill** (an interface manual for AI Agents): <https://ashareapi.com/en/skill/>

## Version history

**Current version: `0.3.1`** (2026-11-24)

| Version | Changes |
|---|---|
| `0.3.1` | **Every endpoint has a method (102 in total)**: batches 8 · L2 order flow 7 · dragon-tiger 2 · sentiment boards 7 · AI Agent 8 · protocol-compatible 3 · watchlist 3 · futures/forex 2 · other 14; `screen()` takes semantic options (`filters`/`sort`/`board`/`mode`, old form still works); `_post()` accepts a JSON body; 429 retry and 4xx handling fixed; example corrected — `quote()` returns 30 trading days |
| `0.2.0` | New quant methods `backtest()` / `backtest_batch()` / `strategies()` / `factors()` / `playbooks()`; added `kline_full()` (full-history K-line) and `ip_whitelist()`; POST/DELETE support in the core |
| `0.1.11` | New `minute()` intraday method; `kline()` now supports minute bars `m1`–`m120` and `start`/`end` date ranges; PoW raise changed from 60/min to 15/min |
| `0.1.10` | 429 message now states the anonymous quota precisely (max **250 rows** per request / **100k rows** per day) · distinguishes "per-minute rate exceeded" from "daily row cap exceeded" (PoW does **not** help for the latter) · no behavior change |
| `0.1.9` | Documentation: README gains "Requirements", "Return shapes" and "Examples" · added GitHub repo / Issues links and the CI badge · source comments and docs wording aligned (no behavior change) |
| `0.1.8` | Documentation wording: price convention (forward-adjusted) unified across README / method docs / CHANGELOG · MCP URL and Agent Skill descriptions clarified |
| `0.1.7` | Documentation: **MCP server URL** `https://api.ashareapi.com/mcp` made explicit · **Agent Skill** section added (`/skill`) · changelog links switched to clickable absolute URLs |
| `0.1.6` | Documentation: `kline()` now states the **price convention** (forward-adjusted · no `adjust` parameter · do not double-adjust) |
| `0.1.5` | Documentation: turnover field example updated to `turnover` · added the `0.1.3` / `0.1.4` rows · metadata `Changelog` points to the site changelog |
| `0.1.4` | `finance()` now **returns the table list as-is** · `shareholder()` / `calendar()` sectioned structures locked down · User-Agent version unified |
| `0.1.3` | Documentation revision (`snapshot()` / `orderbook()` boundaries) · added `CHANGELOG.md` + `MANIFEST.in` |
| `0.1.2` | Added `snapshot()` (full-field profile) · methods 31 → 32 |
| `0.1.1` | Added `orderbook()` (5-level depth) · methods 30 → 31 |
| `0.1.0` | First release (30 methods · 5 free endpoints) |

> **The endpoints themselves are always current** (the service evolves server-side, **no SDK upgrade needed**) — upgrading only gets you the **new convenience methods**.

Full changelog → `CHANGELOG.md` in the package · [site changelog](https://ashareapi.com/en/changelog/) · [PyPI release history](https://pypi.org/project/ashareapi/#history)

## License

MIT · Data is for research reference only and is not investment advice
