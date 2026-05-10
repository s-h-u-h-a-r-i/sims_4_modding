import time
from typing import Optional

__all__ = ("allow_send",)

_min_interval_s = 2.0
_last: float = 0.0


def allow_send(now: Optional[float] = None) -> bool:
    global _last
    t = time.monotonic() if now is None else now
    if t - _last < _min_interval_s:
        return False
    _last = t
    return True
