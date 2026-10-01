<div align="center">

<a href="https://ashareapi.com/en/"><img src="https://ashareapi.com/icon-512.png" width="88" height="88" alt="ashareapi"></a>

# ashareapi — Official Python SDK for the A-Share Data API

**Quotes / K-lines / Financials / Money flow / Dragon-Tiger list / Sectors / Factor screening** — 32 endpoints, and the **free endpoints require no sign-up**.

![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-supported-150458?logo=pandas&logoColor=white)
[![PyPI](https://img.shields.io/pypi/v/ashareapi?label=PyPI)](https://pypi.org/project/ashareapi/)
[![CI](https://github.com/ashareapi/ashareapi-python/actions/workflows/ci.yml/badge.svg)](https://github.com/ashareapi/ashareapi-python/actions/workflows/ci.yml)
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

## 30-second quickstart

```python
from ashareapi import AShareAPI

cli = AShareAPI()                     # free endpoints need no key
df = cli.quote("sh600667")            # real-time quote → DataFrame
print(df[["date", "last", "turnover"]])

print(cli.kline("600667.SH", count=5))  # any code format works (auto-normalized)
print(cli.hot(limit=10))                # hot-search ranking
```

**Paid endpoints** (financials / money flow / Dragon-Tiger list / screening, etc.) need a key — [get one](https://ashareapi.com/en/pricing/) from ¥9.9:

```python
cli = AShareAPI("ct-your-key")          # or set the ASHARE_API_KEY env var
df = cli.screen(preset="low_pe", orderby="ROETTM", limit=10)
print(df.head())
```

## Why use it

- **Free endpoints are genuinely key-free**: `quote / kline / hot / market-overview / changedist` work immediately, no registration
- **Ticker format tolerant**: `sh600667` / `600667.SH` / `600667` all accepted (drop it into existing projects as-is)
- **Automatic source failover**: 70 data sources back each other up on the backend; a failed fetch switches source automatically and **does not consume your quota**
- **Clear error taxonomy**: `AuthError` / `RateLimitError` / `UpstreamError` / `EmptyResultError` (no data ≠ failure) — each one tells you what to do next
- **pandas is optional**: works without pandas too (returns `list[dict]`)

## Endpoints

| Method | Description | Key-free |
|---|---|---|
| `quote(code)` | Real-time quote snapshot | ✅ |
| `kline(code, period, count)` | K-line (daily / weekly / monthly) · **always forward-adjusted (qfq)** | ✅ |
| `hot(limit)` | Hot-search ranking | ✅ |
| `market_overview(type)` | Market overview (profile / valuation / style rotation) | ✅ |
| `changedist()` | Advance-decline distribution (market breadth) | ✅ |
| `finance(code, num)` | The three financial statements | — |
| `fund(code)` | Money flow + Dragon-Tiger list + block trades + margin trading | — |
| `technical(code)` | MA / MACD / KDJ / RSI / BOLL | — |
| `lhb(type)` | Dragon-Tiger sub-rankings (institutions / hot money / active seats) | — |
| `screen(expr/preset, ...)` | Factor screening | — |
| `search(q)` | Search with disambiguation | — |

> ⚠️ **K-line prices are always forward-adjusted (qfq)** — no gaps on ex-dividend dates, and there is **no** `adjust` parameter. **Do not adjust them yourself** (that would double-adjust).

(All 32 endpoints: [endpoint list](https://ashareapi.com/en/endpoints/))

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

> ⚠️ **Three return shapes**: most endpoints are a **single table** → `DataFrame`; `finance()` returns a **list of tables** (`list[list[dict]]`); `shareholder()` / `calendar()` return a **sectioned structure** (`{tables, data}`, kept as a plain dict). The latter two are **not** wrapped into a DataFrame.

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

## Also works with AI agents (MCP / Agent Skill)

Besides the Python SDK, we offer two ways to plug into **AI agents**:

- **MCP server** (Streamable HTTP) — server URL **`https://api.ashareapi.com/mcp`**
  (⚠️ use **that** endpoint URL; the site page `ashareapi.com/en/mcp/` is the **guide**, not the endpoint)
- **Per-client configuration** (Claude Code / Cursor / VS Code / Codex and **19 clients** in total, every key name checked against official docs):
  <https://ashareapi.com/en/mcp/>
- **Agent Skill** (an endpoint manual for AI agents + a downloadable package; drop it into your skills directory): <https://ashareapi.com/en/skill/>

> Free tools/endpoints need **no key**; paid tools take `Authorization: Bearer <your-key>` in the request header.

## Examples

Runnable examples live in [`examples/`](https://github.com/ashareapi/ashareapi-python/tree/main/examples):

| File | What it does |
|---|---|
| [`examples/quickstart.py`](https://github.com/ashareapi/ashareapi-python/blob/main/examples/quickstart.py) | Fetch **quotes / K-lines / hot search** from free endpoints (no key) + commented examples for paid endpoints |

```bash
python examples/quickstart.py
```

## Requirements

- **Python ≥ 3.9**
- Only depends on [`requests`](https://pypi.org/project/requests/) (≥ 2.28)
- `pandas` optional: installed → returns `DataFrame`, not installed → returns `list[dict]`
- Example code: [`examples/quickstart.py`](https://github.com/ashareapi/ashareapi-python/blob/main/examples/quickstart.py)

## Version history

**Current version: `0.1.9`** (2026-09-30)

| Version | Changes |
|---|---|
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

> ⚠️ **The endpoints themselves are always current** (the service evolves server-side, **no SDK upgrade needed**) — upgrading only gets you the **new convenience methods**.

Full changelog → `CHANGELOG.md` in the package · [site changelog](https://ashareapi.com/en/changelog/) · [PyPI release history](https://pypi.org/project/ashareapi/#history)

## License

MIT · Data is for research reference only and is not investment advice
