import enum

from date_and_time import TimeSpan

class ClockSpeedMode(enum.IntEnum):
    PAUSED = 0
    NORMAL = 1
    SPEED2 = 2
    SPEED3 = 3
    INTERACTION_STARTUP_SPEED = 4
    SUPER_SPEED3 = 5

class GameClock:
    @property
    def clock_speed(self) -> ClockSpeedMode: ...

def interval_in_real_seconds(seconds: float) -> TimeSpan: ...
