"""A股数据 API 官方 Python SDK

>>> from ashareapi import AShareAPI
>>> cli = AShareAPI()                 # 免费端点（quote/kline/hot/market-overview/changedist）无需 Key
>>> cli.quote("sh600667")

>>> cli = AShareAPI("ct-你的Key")      # 付费端点需 Key（也读环境变量 ASHARE_API_KEY）
>>> cli.screen(preset="low_pe", limit=10)

文档：https://ashareapi.com/docs  ·  端点清单：https://ashareapi.com/endpoints
"""
from .client import AShareAPI, __version__
from .errors import (AShareError, APIError, AuthError, EmptyResultError, RateLimitError,
                     UpstreamError)

__all__ = ["AShareAPI", "AShareError", "AuthError", "RateLimitError", "EmptyResultError",
           "UpstreamError", "APIError", "__version__"]
