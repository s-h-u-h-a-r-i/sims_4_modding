"""Registered action names → in-game handlers."""

from __future__ import annotations

import typing

from sims.sim_info import SimInfo

from .handlers import apply_go_home, apply_summon_sim

__all__ = ("ACTION_HANDLERS",)


ActionHandler = typing.Callable[[SimInfo], typing.Tuple[bool, typing.Optional[str]]]

ACTION_HANDLERS: typing.Mapping[str, ActionHandler] = {
    "summon_sim": apply_summon_sim,
    "go_home": apply_go_home,
}
