"""
hooks.py — game event hooks.

Monkey-patches VenueService so we get a callback after every save finishes
loading (same pattern used by MCCC). Add further hooks here as needed.
"""

from typing import TYPE_CHECKING

from venues.venue_service import VenueService

if TYPE_CHECKING:
    pass

_orig_venue_loading_finished = VenueService.on_loading_screen_animation_finished


def _on_venue_loading_finished(self, *args, **kwargs):
    result = _orig_venue_loading_finished(self, *args, **kwargs)
    # TODO: call director.on_zone_loaded() here
    return result


VenueService.on_loading_screen_animation_finished = _on_venue_loading_finished
