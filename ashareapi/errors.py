"""异常类型（按用户能采取的动作分类，不只按 HTTP 码）"""


class AShareError(Exception):
    """SDK 异常基类"""


class AuthError(AShareError):
    """401 / 缺 Key —— 动作：检查 ASHARE_API_KEY 或去 https://ashareapi.com/pricing 获取"""


class RateLimitError(AShareError):
    """429 超频 —— 动作：降频重试；或解一次 PoW 挑战提额到 60 次/分（GET /v1/challenge，只提每分钟次数）；若为每日条数用尽，解 PoW 无效 —— 次日恢复或升级档位"""


class EmptyResultError(AShareError):
    """当前**无数据**（≠ 取数失败）—— 如当天无大宗交易。

    **不扣调用次数**；稍后重试或换条件即可。
    区别于 :class:`UpstreamError`（上游取数失败、已自动换源）。
    """


class UpstreamError(AShareError):
    """ok=false（上游取数失败）—— 我们已**自动换源且不扣次数**，动作：重试一次通常就好"""


class APIError(AShareError):
    """5xx / 其他非预期响应"""
