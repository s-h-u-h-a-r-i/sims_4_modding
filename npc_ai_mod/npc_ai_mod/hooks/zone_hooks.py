"""
Monkey-patch Sims 4 zone lifecycle so the director arms after load and tears down
on exit.

``director`` is imported inside callbacks so importing this module does not eagerly
load the orchestration stack.
"""

from __future__ import annotations

import typing

from venues.venue_service import VenueService
from zone import Zone

_orig_venue_loading_finished = VenueService.on_loading_screen_animation_finished  # type: ignore[attr-defined]
_orig_zone_teardown = Zone.on_teardown


def _on_venue_loading_finished(self, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
    result = _orig_venue_loading_finished(self, *args, **kwargs)
    from ..director import director

    director.on_zone_loaded()
    return result


def _on_zone_teardown(self, *args: typing.Any, **kwargs: typing.Any) -> typing.Any:
    from ..director import director

    director.on_zone_unloaded()
    return _orig_zone_teardown(self, *args, **kwargs)


VenueService.on_loading_screen_animation_finished = _on_venue_loading_finished  # type: ignore[attr-defined]
Zone.on_teardown = _on_zone_teardown
