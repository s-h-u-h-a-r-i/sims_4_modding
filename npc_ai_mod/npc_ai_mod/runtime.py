"""Thin wrappers around live game services (clock, etc.)."""

import services
from clock import ClockSpeedMode


def is_game_paused() -> bool:
    try:
        return services.game_clock_service().clock_speed == ClockSpeedMode.PAUSED
    except Exception:
        return False
