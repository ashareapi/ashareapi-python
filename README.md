<div align="center">

<a href="https://ashareapi.com"><img src="https://ashareapi.com/icon-512.png" width="88" height="88" alt="ashareapi"></a>

# ashareapi — A股数据 API 官方 Python SDK

**行情 / K线 / 财务 / 资金 / 龙虎榜 / 板块 / 因子选股** —— 32 个端点，**免费端点无需注册**。

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

## 30 秒上手

```python
from ashareapi import AShareAPI

cli = AShareAPI()                     # 免费端点无需 Key
df = cli.quote("sh600667")            # 实时行情 → DataFrame
print(df[["date", "last", "turnover"]])

print(cli.kline("600667.SH", count=5))  # 代码格式随便写（自动归一化）
print(cli.hot(limit=10))                # 热搜榜
```

**付费端点**（财务 / 资金 / 龙虎榜 / 选股等）需要 Key（[获取](https://ashareapi.com/pricing)，¥9.9 起）：

```python
cli = AShareAPI("ct-你的Key")          # 或设环境变量 ASHARE_API_KEY
df = cli.screen(preset="low_pe", orderby="ROETTM", limit=10)
print(df.head())
```

## 为什么用它

- **免费端点真的免 Key**：`quote / kline / hot / market-overview / changedist` 直接调，无需注册
- **代码格式兼容**：`sh600667` / `600667.SH` / `600667` 都认（不同写法的项目都能直接用）
- **多源自动切换**：后端 70 个数据源互为备份，取数失败会自动换源且**不扣调用次数**
- **错误分类清楚**：`AuthError` / `RateLimitError` / `UpstreamError` / `EmptyResultError`（无数据 ≠ 失败）—— 每类都告诉你该做什么
- **pandas 可选**：不想装 pandas 也能用（返回 `list[dict]`）

## 端点一览

| 方法 | 说明 | 免 Key |
|---|---|---|
| `quote(code)` | 实时行情快照 | ✅ |
| `kline(code, period, count)` | K 线（日/周/月）· **口径固定为前复权** | ✅ |
| `hot(limit)` | 热搜榜 | ✅ |
| `market_overview(type)` | 市场总览（画像/估值/风格轮动）| ✅ |
| `changedist()` | 涨跌分布（市场广度）| ✅ |
| `finance(code, num)` | 三大报表 | — |
| `fund(code)` | 资金流 + 龙虎榜 + 大宗 + 两融 | — |
| `technical(code)` | MA / MACD / KDJ / RSI / BOLL | — |
| `lhb(type)` | 龙虎榜分榜（机构 / 游资 / 活跃席位）| — |
| `screen(expr/preset, ...)` | 因子选股 | — |
| `search(q)` | 搜索消歧 | — |

> ⚠️ **K 线价格口径固定为前复权**（除权除息日不跳空；**没有** `adjust` 参数）—— **不要再自己复权**（会二次复权）。

（完整 32 端点见 [端点清单](https://ashareapi.com/endpoints)）

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

> ⚠️ **三种返回形态**：多数端点是**单表** → `DataFrame`；`finance()` 是**表列表**（`list[list[dict]]`）；`shareholder()` / `calendar()` 是**多段结构**（`{tables, data}`，原样 dict）。后两种**不会**被套成 DataFrame。

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
except UpstreamError as e:      # 上游取数失败（已自动换源、不扣次数）→ 重试一次通常就好
    print(e)
except EmptyResultError as e:   # 当前无数据（如当天无大宗交易）→ 不计费，换条件或稍后再试
    print(e)
```

## 也用 AI Agent（MCP / Agent Skill）

除了 Python SDK，我们还提供两种 **AI Agent** 接入方式：

- **MCP 服务器**（Streamable HTTP）—— 服务器地址 **`https://api.ashareapi.com/mcp`**
  （⚠️ 填**这个**接口地址；站点介绍页 `ashareapi.com/mcp` **不是**接口）
- **各客户端配置写法**（Claude Code / Cursor / VS Code / Codex 等 **19 家**，键名差异都核对过官方文档）：
  <https://ashareapi.com/mcp>
- **Agent Skill**（给 AI Agent 读的接口说明书 + 分发包，装进 skills 目录即用）：<https://ashareapi.com/skill>

> 免费工具/端点**无需 Key**；付费工具在请求头带 `Authorization: Bearer <你的 Key>`。

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

## 版本记录

**当前版本：`0.1.9`**（2026-09-30）

| 版本 | 变更 |
|---|---|
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

> ⚠️ **端点本身永远是最新的**（服务端演进，**无需升级 SDK**）—— 升级只是为了用上**新增的便利方法**。

完整变更记录 → 包内 `CHANGELOG.md` · [站内更新日志](https://ashareapi.com/changelog) · [PyPI 版本历史](https://pypi.org/project/ashareapi/#history)

## License

MIT · 数据仅供研究参考，不构成投资建议
