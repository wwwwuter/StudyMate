"""时间工具：返回「无时区、UTC 值」的 datetime。

MySQL DATETIME 不存时区信息，统一用 naive UTC 既能消除 datetime.utcnow()
的 DeprecationWarning，也避免 tz-aware / naive 混用导致的比较偏差。
"""
from datetime import datetime, timezone


def utcnow():
    """等价于旧 datetime.utcnow()，但无弃用告警。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
