"""3 行拿数据（免费端点无需 Key）"""
from ashareapi import AShareAPI

cli = AShareAPI()                                   # 免费端点：无需注册、无需 Key

bar = cli.quote("sh600667")                         # 行情快照
print("最新行情：")
print(bar[["date", "last", "turnover"]].to_string(index=False) if hasattr(bar, "columns") else bar)

print("\n最近 5 根日线：")
k = cli.kline("600667.SH", count=5)                 # 代码格式随便写（自动归一化）· 口径固定前复权，别再自己复权
print(k.to_string(index=False) if hasattr(k, "columns") else k)

print("\n热搜 Top 5：")
print(cli.hot(limit=5).to_string(index=False))

# 付费端点（需 Key）—— 取消注释并填入你的 Key：
# cli = AShareAPI("ct-你的Key")
# print(cli.screen(expr="intersect([PE_TTM > 0, PE_TTM < 20, ROETTM > 15])", orderby="ROETTM", limit=10))
