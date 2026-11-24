"""3 行拿数据（免费端点无需 Key）

⚠️ 匿名档限 5 次/分：本示例一次跑 3 个端点，连续重跑会收到 429。
   加 Key（或两次运行之间隔 12 秒以上）即可。
"""
from ashareapi import AShareAPI

cli = AShareAPI()                                   # 免费端点：无需注册、无需 Key

bar = cli.quote("sh600667")                         # 最近 30 个交易日的行情（每条标的一行/天）
print("最近行情（30 个交易日）：")
print(bar[["date", "last", "turnover"]].to_string(index=False) if hasattr(bar, "columns") else bar)

print("\n最近 5 根日线：")
k = cli.kline("600667.SH", count=5)                 # 代码格式随便写（自动归一化）· 口径固定前复权，别再自己复权
print(k.to_string(index=False) if hasattr(k, "columns") else k)

print("\n热搜 Top 5：")
print(cli.hot(limit=5).to_string(index=False))

# 付费端点（需 Key）—— 取消注释并填入你的 Key：
# cli = AShareAPI("ct-你的Key")
# print(cli.screen(filters="pe_ttm:0..20,roe_ttm:>=15", sort="roe_ttm", limit=10))
