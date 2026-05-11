"""Registered action names → in-game handlers."""

from __future__ import annotations

import typing

from sims.sim_info import SimInfo

from .handlers.go_home import apply_go_home

ActionHandler = typing.Callable[[SimInfo], typing.Tuple[bool, typing.Optional[str]]]

ACTION_HANDLERS: typing.Mapping[str, ActionHandler] = {
    "go_home": apply_go_home,
}
