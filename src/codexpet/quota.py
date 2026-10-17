"""Pure quota interpretation. Unknown values must never become zero."""
from dataclasses import dataclass
from datetime import datetime
import math
import time


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


@dataclass(frozen=True)
class Window:
    used: float | None
    minutes: float | None
    resets_at: float | None

    @property
    def remaining(self):
        return None if self.used is None else max(0.0, min(100.0, 100.0 - self.used))

    @property
    def label(self):
        if self.minutes is None:
            return '额度窗口'
        if self.minutes == 10080:
            return '每周额度'
        if self.minutes >= 1440 and self.minutes % 1440 == 0:
            return f'{self.minutes / 1440:g} 天额度'
        if self.minutes >= 60 and self.minutes % 60 == 0:
            return f'{self.minutes / 60:g} 小时额度'
        return f'{self.minutes:g} 分钟额度'

    def reset_due(self, now=None):
        return self.resets_at is not None and self.resets_at <= (time.time() if now is None else now)


@dataclass(frozen=True)
class Snapshot:
    primary: Window | None
    secondary: Window | None
    plan: str
    fetched_at: float

    def stale(self, now=None):
        now = time.time() if now is None else now
        return now - self.fetched_at > 300 or any(w and w.reset_due(now) for w in (self.primary, self.secondary))


def parse_window(raw):
    if not isinstance(raw, dict):
        return None
    minutes = number(raw.get('windowDurationMins'))
    resets = number(raw.get('resetsAt'))
    return Window(number(raw.get('usedPercent')), minutes if minutes and minutes > 0 else None,
                  resets if resets and 0 < resets < 253402300799 else None)


def parse_snapshot(result, now=None):
    if not isinstance(result, dict):
        raise ValueError('没有收到有效的额度数据')
    buckets = result.get('rateLimitsByLimitId')
    if isinstance(buckets, dict):
        raw = buckets.get('codex')
    else:
        raw = result.get('rateLimits')
    if not isinstance(raw, dict) or raw.get('limitId') not in (None, 'codex'):
        raise ValueError('当前账号未返回 Codex 额度，请确认 CLI 使用 ChatGPT 账号登录')
    primary, secondary = parse_window(raw.get('primary')), parse_window(raw.get('secondary'))
    if not any(w is not None and w.remaining is not None for w in (primary, secondary)):
        raise ValueError('当前账号未提供可显示的额度；请确认使用 ChatGPT 账号登录')
    plan = raw.get('planType')
    plan = plan.title() if isinstance(plan, str) and len(plan) < 30 else 'Codex'
    return Snapshot(primary, secondary, plan, time.time() if now is None else now)


def reset_text(window, now=None):
    if window is None or window.resets_at is None:
        return '重置时间暂不可用'
    seconds = max(0, int(window.resets_at - (time.time() if now is None else now)))
    if seconds == 0:
        return '已到重置时间，等待刷新'
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    if days:
        return f'{days} 天 {hours} 小时后重置'
    if hours:
        return f'{hours} 小时 {minutes} 分钟后重置'
    return f'{minutes} 分钟后重置' if minutes else '不到 1 分钟后重置'


def reset_date(window):
    if window is None or window.resets_at is None:
        return '—'
    try:
        return datetime.fromtimestamp(window.resets_at).strftime('%m/%d %H:%M')
    except (ValueError, OSError, OverflowError):
        return '—'
