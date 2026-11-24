<div align="center">

<a href="https://ashareapi.com"><img src="https://ashareapi.com/icon-512.png" width="88" height="88" alt="ashareapi"></a>

# ashareapi — A股数据 API 官方 Python SDK

**行情（分时 · 五档盘口）/ K线 / 财务 / 资金 / 龙虎榜 / L2 大单 / 板块 / 因子选股 / 量化回测 / 短线打板 / 集合竞价 / 资讯公告** —— **102 个端点**，**免费端点无需注册**。

![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-supported-150458?logo=pandas&logoColor=white)
[![PyPI](https://img.shields.io/pypi/v/ashareapi?label=PyPI)](https://pypi.org/project/ashareapi/)
[![CI](https://github.com/ashareapi/ashareapi-python/actions/workflows/ci.yml/badge.svg)](https://github.com/ashareapi/ashareapi-python/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-MIT-green)

**中文** · [English](README.en.md)

[官网](https://ashareapi.com) · [文档](https://ashareapi.com/docs/) · [端点清单](https://ashareapi.com/endpoints/) · [MCP 接入](https://ashareapi.com/mcp) · [Agent Skill](https://ashareapi.com/skill)

[GitHub 源码](https://github.com/ashareapi/ashareapi-python) · [问题反馈 Issues](https://github.com/ashareapi/ashareapi-python/issues) · [更新日志](https://ashareapi.com/changelog)

</div>

常用端点文档：[K 线](https://ashareapi.com/docs/endpoints/kline/) · [因子选股](https://ashareapi.com/docs/endpoints/screen/) · [健康检查](https://ashareapi.com/docs/endpoints/health/)

```bash
pip install ashareapi            # 基础（返回 list[dict]）
pip install "ashareapi[pandas]"  # 加 DataFrame 支持（推荐）
```

> 也有 **Node.js / TypeScript SDK**：`npm install ashareapi` —— [npm](https://www.npmjs.com/package/ashareapi)

## 这是什么

**A股数据 API 的官方 Python SDK** —— 一行方法直接拿 `DataFrame`：URL 拼接、重试、限频退避、错误分型和返回结构，SDK 都已经替你处理好。`pip install ashareapi` 之后：

```python
from ashareapi import AShareAPI
cli = AShareAPI(api_key="ct-你的Key")   # 或用环境变量 ASHARE_API_KEY
print(cli.quote("sh600667"))            # 行情
print(cli.backtest(code="sh600667", strategy="mom20"))   # 量化回测
```

**10 个端点无需 Key**（装上就能调）：`/v1/quote` · `/v1/kline` · `/v1/hot` · `/v1/market-overview` · `/v1/changedist` · `/v1/wiki` · `/v1/trade-calendar` · `/v1/models` · `/v1/health` · `/v1/challenge`。其余端点需要 Key（[获取](https://ashareapi.com/pricing)，¥9.9 起）。

## 30 秒上手

```python
from ashareapi import AShareAPI

cli = AShareAPI()                     # 免费端点无需 Key
df = cli.quote("sh600667")            # 最近 30 个交易日 → DataFrame
print(df[["date", "last", "turnover"]])

print(cli.kline("600667.SH", count=5))  # 代码格式随便写（自动归一化）
print(cli.hot(limit=10))                # 热搜榜
```

**付费端点**（财务 / 资金 / 龙虎榜 / 选股等）需要 Key（[获取](https://ashareapi.com/pricing)，¥9.9 起）：

```python
cli = AShareAPI("ct-你的Key")          # 或设环境变量 ASHARE_API_KEY
df = cli.screen(preset="low_pe", sort="roe_ttm", limit=10)
print(df.head())
```

## 接入方式（同一个 Key，六种用法）

按你手上的工具选，不用换 Key、不用换套餐：

| 接入方式 | 怎么装 | 覆盖 |
|---|---|---|
| **Python SDK** | `pip install ashareapi` | 脚本 / 回测 / 数据入库 |
| **Node.js / TS SDK** | `npm install ashareapi` | 服务端 / 前端 / 定时任务 |
| **MCP** | 填一个地址 `https://api.ashareapi.com/mcp` | **19 家客户端**（Claude Code / Cursor / Codex / VS Code…）· **94 个工具** |
| **Personal Agent** | 在助理 App 里加 MCP | Today / Grok Bot / Muse / Dots / Duet |
| **Agent Skill** | 放进 skills 目录 | **45+ 客户端**通用 |
| **Pi（pi.dev）** | `npm install ashareapi-pi` | Pi 里直接查，装完即知调哪个端点 |
| **DSH 插件** | 装插件 | DeepSeek Harness |

以上都是原生支持，不是转接层——同一套端点、同一份额度、同一个 Key。细节见下方各节。

## 为什么用它

- **盘中数据不缓存**：每次调用都重新取 · `minute` 分时（当日 242 点）· `auction` 集合竞价分时（9:15–9:25，约 150 个点）
- **K 线 10 年历史**：2016-08-08 起，`kline_full` 一次拿全（约 2,500 根；每只从其**上市日**开始，科创板 2019 上市的就有 1,700 根）；日 / 周 / 月 / 季 / 年 + 分钟线 `m1`~`m120`，**固定前复权**（无 `adjust` 参数，不会二次复权）
- **全市场一次拿**：`market_kline` 一次返回某交易日**全部 A 股（5,000+ 只）**的日线 —— 不用循环 5,000 次（专业版起，1 次折算 500 次额度）
- **L2 微观结构 7 个端点**：全市场主力净额榜**一次 5,568 只** · 龙虎榜席位穿透到**营业部级**（带 `is_youzi`）· 大单四方向 / 挂撤单队列 / 100 日历史大单
- **批量端点 9 个**：行情 / K 线 / 快照 / 财务 / 技术 / 筹码 / 股东 / 资金流 / 公司简况，**一次 150 只约 2 秒**（逐个取 200 只约 5 分钟）
- **一个 Key 覆盖 5 个市场**：A 股 + 场内 ETF（1,716 只）+ 港股（22 个接口）+ 美股（16 个接口）+ 期货外汇（65 个品种）
- **不写代码也能用**：配好 MCP 后直接在对话里问「茅台今天多少」——Claude Code / Cursor / Codex，以及 Today / Grok Bot / Muse 等个人助理（**19 家客户端 · 94 个工具**）
- **量化五位一体**：87 因子 + 29 策略 + 25 方法论 + 回测（单标的 / 组合 / 批量）+ 组合权重优化
- **不该扣的就不扣**：空结果、取数失败、代码传错 —— 都**不计费**（按实际返回只数计）
- **10 个端点免 Key**：`quote / kline / hot / market-overview / changedist / wiki / trade-calendar / models / health / challenge` 直接调，无需注册
- **出问题能定位**：每次响应带 `trace_id`，报障时报这个号，直接查到那一次请求
- **错误分类清楚**：401 → `AuthError`、429 → `RateLimitError`、取数失败 → `UpstreamError`、无数据 → `EmptyResultError`（**无数据 ≠ 失败**）—— 四类都能直接 `except`，不用解析错误字符串
- **代码格式容错**：`sh600667` / `600667.SH` / `600667` 都认
- **多源自动切换**：70 个数据源互为备份，失败自动换源且**不扣调用次数**
- **pandas 可选**：不装也能用（返回 `list[dict]`）

## 端点一览

| 方法 | 说明 | 免 Key |
|---|---|---|
| `quote(code)` | 最近 30 个交易日的行情（每天一行）| ✅ |
| `kline(code, period, count, start, end)` | K 线（日/周/月/季/年 + 分钟线 `m1`~`m120`）· 复权口径由服务端固定（日线及以上前复权 · 分钟线不复权）| ✅ 日线及以上 / 分钟线付费 |
| `minute(code, days)` | **分时**（当日 / 近 5 日盘中走势）· 付费 | — |
| `hot(limit)` | 热搜榜 | ✅ |
| `market_overview(type)` | 市场总览（画像/估值/风格轮动）| ✅ |
| `changedist()` | 涨跌分布（市场广度）| ✅ |
| `finance(code, num)` | 三大报表 | — |
| `fund(code)` | 资金流 + 龙虎榜 + 大宗 + 两融 | — |
| `technical(code)` | MA / MACD / KDJ / RSI / BOLL | — |
| `lhb(type)` | 龙虎榜分榜（机构 / 游资 / 活跃席位）| — |
| `screen(filters=..., sort=..., board=..., mode=...)` | 因子选股 / 条件筛选（语义参数，旧 `expr`/`orderby` 仍兼容） | — |
| `search(q)` | 搜索消歧 | — |
| `kline_full(code, fq, start, end)` | **全历史**日线一次拿全（约 2,500 根 · 2016-08-08 起）· `fq` 可选 `qfq`/`hfq`/`nofq` | — |
| `backtest(strategy, mode, code, ...)` | **量化回测**（单标的实时 / 组合查预置区间 · `weighting` 可选等权或波动率倒数）| — |
| `backtest_batch(codes, strategies, ...)` | **批量回测**（多标的 × 多策略对比矩阵 · ≤20 只 × 10 条）| — |
| `strategies()` | 量化策略清单（20 条单标的 + 9 条组合，含参数范围）| — |
| `factors(category, kind)` | 量化因子库（87 因子 + 50 筛选入口 + 22 预设 + 14 策略模板）| — |
| `playbooks(category, id)` | 量化方法论库（25 条「怎么判断市场」流程）| — |
| `ip_whitelist(action, ips)` | **IP 白名单**（把 Key 锁定到固定 IP · `action` = get/set/clear）| — |


**其余端点方法**（按类分组，每组一行）：

| 分类 | 方法 |
|---|---|
| 批量（一次多只） | `quote_batch` · `kline_batch` · `snapshot_batch` · `profile_batch` · `finance_batch` · `technical_batch` · `chip_batch` · `shareholder_batch` |
| L2 大单 | `bigorder` · `bigorder_flow` · `bigorder_flow_full` · `bigorder_queue` · `bigorder_history` · `bigorder_split` · `bigorder_rank` |
| 龙虎榜 | `lhb_seats` · `lhb_agency` |
| 情绪 / 榜单 | `market_mood` · `limit_reason` · `broken_board` · `tail_chase` · `northbound` · `new_high` · `flash` |
| AI Agent | `agent_search` · `agent_ask` · `agent_research` · `agent_research_status` · `scanner` · `scanner_snapshots` · `analyst` · `evidence` |
| 自选股 | `watchlist` · `watchlist_import` · `watchlist_quotes` |
| 协议兼容 | `messages` · `chat_completions` · `responses`（OpenAI / Anthropic 协议直连，BYOK） |
| 期货 / 外汇 | `futures` · `forex` |
| 其余 | `models` · `trade_calendar` · `index_list` · `index_constituent` · `suspension` · `buyback` · `consensus` · `rating` · `disclosure` · `fund_flow` · `fund_short` · `fund_south` · `score` · `report` · `stocks` |
> **L2 微观结构（7 个端点 · 机构版起）**——券商终端里这一层叫「Level-2 增强」，通常要单独买行情授权；这里是 7 个方法直接调：
> - `bigorder_rank`：**全市场主力净额榜，一次拿 5,568 只**、8 种排序 —— 不是一只一只查
> - `lhb_seats`：龙虎榜席位**穿透到营业部级**，带 `is_youzi` 游资标记
> - 其余 5 个：大单净额分时 · 逐笔大单四方向 · 挂单撤单队列 · 100 日历史大单 · 主力四分解

> **批量端点（9 个）**——多数接口只能一只一只取，200 只要循环 200 次；这里一次传多只：
> - 覆盖：行情 / K 线 / 快照 / 公司简况 / 财务 / 技术指标 / 筹码 / 股东 / 资金流
> - 上限：专业版单次 200 只 · 机构版 1000 只
> - 计费：**按实际返回只数**扣，失败的不扣
> - 一次 150 只日线约 2 秒（逐个取 200 只约 5 分钟）；200 只建议拆成 2 批

> **K 线价格口径固定为前复权**（除权除息日不跳空；**没有** `adjust` 参数）—— **不要再自己复权**（会二次复权）。

（完整 102 端点见 [端点清单](https://ashareapi.com/endpoints)）

## 返回形态

装了 `pandas` 时方法返回 **`DataFrame`**（未装则返回 `list[dict]`），可直接按列名取字段：

```python
df = cli.quote("sh600667")
print(df[["date", "last", "turnover"]])
```

需要**原始信封**（含 `endpoint` / `tier` / `elapsed_ms` / `source`）时用 `raw=True`：

```python
cli = AShareAPI(raw=True)
env = cli.quote("sh600667")
# { 'ok': True, 'endpoint': '/v1/quote', 'tier': 'free', 'elapsed_ms': 862, 'source': '...', 'data': [...] }
```

> **三种返回形态**：多数端点是**单表** → `DataFrame`；`finance()` 是**表列表**（`list[list[dict]]`）；`shareholder()` / `calendar()` 是**多段结构**（`{tables, data}`，原样 dict）。后两种**不会**被套成 DataFrame。

## 错误处理

```python
from ashareapi import AShareAPI, AuthError, RateLimitError, UpstreamError, EmptyResultError

cli = AShareAPI()
try:
    df = cli.fund("sh600667")
except AuthError as e:          # 401 / 缺 Key → 去拿 Key
    print(e)
except RateLimitError as e:     # 429 → 降频 / 解 PoW 挑战提额 / 升级档位
    print(e)
except UpstreamError as e:      # 数据源取数失败（已自动换源、不扣次数）→ 重试一次通常就好
    print(e)
except EmptyResultError as e:   # 当前无数据（如当天无大宗交易）→ 不计费，换条件或稍后再试
    print(e)
```

> **拿原始信封时可以看 `stale`**：`raw=True` 下，若该条数据不是本次实时取到的最新版本，响应会带 `stale: true` 与 `stale_age_s`（距最近一次好数据多少秒），不会静默给旧值。

## 其他接入方式

### MCP 服务器

- 服务器地址 **`https://api.ashareapi.com/mcp`**（填**这个**接口地址；站点介绍页 `ashareapi.com/mcp` **不是**接口）
- 各客户端配置写法（Claude Code / Cursor / VS Code / Codex 等 **19 家**，键名差异都核对过官方文档）：<https://ashareapi.com/mcp>
- **Agent Skill**（给 AI Agent 读的接口说明书 + 分发包，装进 skills 目录即用）：<https://ashareapi.com/skill>

> 免费工具/端点**无需 Key**；付费工具在请求头带 `Authorization: Bearer <你的 Key>`。

### Personal Agent（手机上的个人助理）

不写代码，在助理 App 里配一个 MCP 就能问行情、财报、K 线。

| 助理 | 客户端入口 | 认证 |
|---|---|---|
| **Today** | 设置 → 连接应用 → 添加自定义 MCP | Bearer Token |
| **Grok Bot** | Connect apps → 自定义远程 MCP | Bearer Header |
| **Muse** | Settings → Connectors → Custom Connector | Bearer / OAuth |
| **Dots** | 先在 ChatGPT 里加 connector | 继承 ChatGPT |
| **Duet** | 先在 Claude 里加 connector | 继承 Claude |

统一填：

```
URL:       https://api.ashareapi.com/mcp
Transport: Streamable HTTP
Auth:      Authorization: Bearer <你的 Key>
```

- 必须公网 HTTPS，**不支持 localhost**
- Bearer 下拉框里**只填 Key**，不要再手写 `Bearer`
- 客户端不能填 Header 时，才用 `?key=` 兜底

接上之后可以直接问：「查一下 sh600519 最新行情」「给我 600519 最近 30 天日 K」「今天涨停里成交额最大的 10 只」。
完整步骤见 <https://ashareapi.com/docs/guides/personal-agent/>

## 示例

仓里 [`examples/`](https://github.com/ashareapi/ashareapi-python/tree/main/examples) 有可直接跑的示例：

| 文件 | 做什么 |
|---|---|
| [`examples/quickstart.py`](https://github.com/ashareapi/ashareapi-python/blob/main/examples/quickstart.py) | 免费端点拿**行情 / K 线 / 热搜**（无需 Key）+ 付费端点的注释示例 |

```bash
python examples/quickstart.py
```

## 环境要求

- **Python ≥ 3.9**
- 只依赖 [`requests`](https://pypi.org/project/requests/)（≥ 2.28）
- `pandas` 可选：装了返回 `DataFrame`，不装返回 `list[dict]`
- 示例代码见 [`examples/quickstart.py`](https://github.com/ashareapi/ashareapi-python/blob/main/examples/quickstart.py)

## 相关

**官方 SDK**：Python `pip install ashareapi` · Node.js / TypeScript `npm install ashareapi`

**MCP 服务器**：`https://api.ashareapi.com/mcp`（[配置说明](https://ashareapi.com/mcp)）

**Agent Skill**（给 AI Agent 读的接口说明书）：<https://ashareapi.com/skill>

## 版本记录

**当前版本：`0.3.1`**（2026-11-24）

| 版本 | 变更 |
|---|---|
| `0.3.1` | **每个端点都有对应方法（共 102 个）**：批量 8 · L2 大单 7 · 龙虎榜 2 · 情绪榜单 7 · AI Agent 8 · 协议兼容 3 · 自选股 3 · 期货外汇 2 · 其余 14；`screen()` 改用语义参数（`filters`/`sort`/`board`/`mode`，旧写法仍可用）；`_post()` 支持 JSON 请求体；修复 429 重试与 4xx 错误处理；示例修正 `quote()` 返回 30 个交易日 |
| `0.2.0` | 新增量化方法 `backtest()` / `backtest_batch()` / `strategies()` / `factors()` / `playbooks()`；补 `kline_full()` 全历史 K 线、`ip_whitelist()` IP 白名单；底层支持 POST/DELETE |
| `0.1.11` | 新增 `minute()` 分时方法；`kline()` 支持分钟线 `m1~m120` 与 `start`/`end` 日期范围；解 PoW 提额由 60 次/分调为 15 次/分 |
| `0.1.10` | 429 提示补充匿名额度口径（单次最多 250 条 / 每天最多 10 万条）· 区分「每分钟次数超」与「当天条数超」（后者解 PoW 无效）· 无行为变更 |
| `0.1.9` | 文档完善：README 新增「环境要求」「返回形态」「示例」· 补 GitHub 仓 / Issues 链接与 CI 徽章 · 源码注释与文档表述统一（无行为变更）|
| `0.1.8` | 文档措辞修订：价格口径（前复权）在 README / 方法文档 / CHANGELOG 中表述统一 · MCP 地址与 Agent Skill 说明更明确 |
| `0.1.7` | 文档：明确 **MCP 服务器地址** `https://api.ashareapi.com/mcp` · 新增 **Agent Skill** 说明（`/skill`）· 变更记录链接改为可直接点开的绝对地址 |
| `0.1.6` | 文档：`kline()` 写明**价格口径**（前复权 · 无 `adjust` 参数 · 勿二次复权）|
| `0.1.5` | 文档：换手率字段示例更新为 `turnover` · 补齐 `0.1.3` / `0.1.4` 两行 · 元数据 `Changelog` 指向站内更新日志 |
| `0.1.4` | `finance()` **原样返回表列表** · `shareholder()` / `calendar()` 多段结构锁定 · User-Agent 版本号统一 |
| `0.1.3` | 文档修订（`snapshot()` / `orderbook()` 边界）· 新增 `CHANGELOG.md` + `MANIFEST.in` |
| `0.1.2` | 新增 `snapshot()`（全字段画像）· 方法数 31 → 32 |
| `0.1.1` | 新增 `orderbook()`（五档盘口）· 方法数 30 → 31 |
| `0.1.0` | 首个版本（30 个方法 · 5 个免费端点）|

> **端点本身永远是最新的**（服务端演进，**无需升级 SDK**）。升级 SDK 可以拿到新端点的对应方法，以及请求处理（重试、限频退避、错误分型）的最新改进。



完整变更记录 → 包内 `CHANGELOG.md` · [站内更新日志](https://ashareapi.com/changelog) · [PyPI 版本历史](https://pypi.org/project/ashareapi/#history)



## License

MIT · 数据仅供研究参考，不构成投资建议
