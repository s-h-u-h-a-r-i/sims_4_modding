from typing import Any, Callable
from date_and_time import TimeSpan

class AlarmHandle:
    def cancel(self) -> None: ...

def add_alarm_real_time(
    owner: Any,
    time_span: TimeSpan,
    callback: Callable[[AlarmHandle], None],
    repeating: bool = ...,
    use_sleep_time: bool = ...,
    cross_zone: bool = ...,
) -> AlarmHandle: ...

def cancel_alarm(handle: AlarmHandle) -> None: ...
