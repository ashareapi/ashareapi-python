"""异常类型（按用户能采取的动作分类，不只按 HTTP 码）"""


class AShareError(Exception):
    """SDK 异常基类"""


class AuthError(AShareError):
    """401 / 403 / 缺 Key —— 动作：检查 ``ASHARE_API_KEY``；403 多为**档位不够**
    （如分钟线需 standard）⇒ 去 https://ashareapi.com/pricing 升级"""


class RateLimitError(AShareError):
    """429 超频 —— 动作：降频重试；或解一次 PoW 挑战提额到 15 次/分（GET /v1/challenge，只提每分钟次数）；若为每日条数用尽，解 PoW 无效 —— 次日恢复或升级档位"""


class EmptyResultError(AShareError):
    """当前**无数据**（≠ 取数失败）—— 如当天无大宗交易。

    **不扣调用次数**；稍后重试或换条件即可。
    区别于 :class:`UpstreamError`（数据源取数失败、已自动换源）。
    """


class UpstreamError(AShareError):
    """ok=false（数据源取数失败）—— 我们已**自动换源且不扣次数**，动作：重试一次通常就好"""


class APIError(AShareError):
    """5xx / 其他 4xx / 非预期响应

    其他 4xx 的**含义写在异常消息里**（服务端原话），常见两类：
      · ``413`` —— 单次条数超限（如 ``/v1/kline`` 标的数 × ``count`` > 60000）⇒ 拆请求或调小 count
      · ``422`` —— 请求参数超限 / 不合法（如匿名单次 >5 只标的、``period`` 取值错）
    这两类**重试无意义**（不是限流、不是数据源抖动），照消息改参数即可。
    """
